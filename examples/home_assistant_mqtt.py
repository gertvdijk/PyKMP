# SPDX-FileCopyrightText: 2024 The PyKMP contributors
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import decimal
import json
import logging
import os
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Sequence

try:
    import paho.mqtt.client as mqtt
except ImportError as exc:  # pragma: no cover - helper script
    raise SystemExit(
        "Missing dependency 'paho-mqtt'. Install with: pip install paho-mqtt"
    ) from exc

from pykmp import constants, messages
from pykmp.client import PySerialClientCommunicator
from pykmp.codec import FloatCodec

LOGGER = logging.getLogger("pykmp-ha-mqtt")

DEFAULT_REGISTERS: tuple[int, ...] = (60, 68, 80, 74, 86, 87, 266)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_registers(value: str | None) -> tuple[int, ...]:
    if value is None:
        return DEFAULT_REGISTERS

    registers: list[int] = []
    for part in value.split():
        registers.append(int(part, base=0))
    return tuple(registers)


@dataclass(slots=True)
class Settings:
    serial_device: str
    destination_address: int
    registers: tuple[int, ...]
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str | None
    mqtt_password: str | None
    mqtt_base_topic: str
    mqtt_discovery_prefix: str
    mqtt_client_id: str | None
    mqtt_retain: bool
    mqtt_discovery: bool
    interval_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        mqtt_host = os.getenv("MQTT_HOST")
        if not mqtt_host:
            raise SystemExit("MQTT_HOST is required.")

        return cls(
            serial_device=os.getenv("PYKMP_SERIAL_DEVICE", "/dev/ttyUSB0"),
            destination_address=int(
                os.getenv(
                    "PYKMP_DESTINATION_ADDRESS",
                    str(constants.DestinationAddress.HEAT_METER.value),
                ),
                base=0,
            ),
            registers=_parse_registers(os.getenv("PYKMP_REGISTERS")),
            mqtt_host=mqtt_host,
            mqtt_port=int(os.getenv("MQTT_PORT", "1883"), base=10),
            mqtt_username=os.getenv("MQTT_USERNAME"),
            mqtt_password=os.getenv("MQTT_PASSWORD"),
            mqtt_base_topic=os.getenv("MQTT_BASE_TOPIC", "pykmp"),
            mqtt_discovery_prefix=os.getenv("MQTT_DISCOVERY_PREFIX", "homeassistant"),
            mqtt_client_id=os.getenv("MQTT_CLIENT_ID"),
            mqtt_retain=_env_bool("MQTT_RETAIN", True),
            mqtt_discovery=_env_bool("MQTT_DISCOVERY", True),
            interval_seconds=int(os.getenv("PYKMP_INTERVAL_SECONDS", "300"), base=10),
        )


@dataclass(slots=True)
class RegisterReading:
    id_: int
    id_hex: str
    name: str
    unit: str
    unit_int: int
    unit_hex: str
    value: float
    text: str
    ha_unit: str
    ha_value: float
    ha_value_str: str


HA_CLASS_BY_UNIT: dict[str, tuple[str | None, str | None]] = {
    # Only HA-supported unit/device_class combos to avoid warnings.
    "Wh": ("energy", "total_increasing"),
    "kWh": ("energy", "total_increasing"),
    "MWh": ("energy", "total_increasing"),
    "GWh": ("energy", "total_increasing"),
    "W": ("power", "measurement"),
    "kW": ("power", "measurement"),
    "MW": ("power", "measurement"),
    "GW": ("power", "measurement"),
    "°C": ("temperature", "measurement"),
    "m³": ("volume", "total_increasing"),
    "m³/h": ("volume_flow_rate", "measurement"),
    "bar": ("pressure", "measurement"),
    "V": ("voltage", "measurement"),
    "A": ("current", "measurement"),
}


def read_serial(settings: Settings) -> str | None:
    try:
        communicator = PySerialClientCommunicator(serial_device=settings.serial_device)
        response = communicator.send_request(
            message=messages.GetSerialRequest(),
            destination_address=settings.destination_address,
        )
    except TimeoutError:
        LOGGER.warning("Timed out while reading meter serial.")
        return None
    except Exception:
        LOGGER.exception("Failed to read meter serial.")
        return None

    serial = str(response.serial)
    LOGGER.info("Meter serial: %s", serial)
    return serial


def read_registers(settings: Settings) -> list[RegisterReading]:
    try:
        communicator = PySerialClientCommunicator(serial_device=settings.serial_device)
        response = communicator.send_request(
            message=messages.GetRegisterRequest(
                registers=[messages.RegisterID(reg) for reg in settings.registers]
            ),
            destination_address=settings.destination_address,
        )
    except TimeoutError:
        LOGGER.warning("Timed out while reading registers.")
        return []
    except Exception:
        LOGGER.exception("Failed to read registers.")
        return []

    readings: list[RegisterReading] = []
    for reg in response.registers.values():
        name = constants.REGISTERS.get(reg.id_, f"Register {reg.id_}")
        unit = constants.UNITS_NAMES.get(reg.unit, f"unit-{reg.unit}")
        value_dec = FloatCodec.decode(reg.value)
        ha_unit = unit
        ha_value_dec = value_dec
        if unit == "l/h":
            ha_unit = "m³/h"
            ha_value_dec = value_dec / decimal.Decimal("1000")
        readings.append(
            RegisterReading(
                id_=reg.id_,
                id_hex=f"0x{reg.id_:04X}",
                name=name,
                unit=unit,
                unit_int=reg.unit,
                unit_hex=f"0x{reg.unit:02X}",
                value=float(value_dec),
                text=str(value_dec),
                ha_unit=ha_unit,
                ha_value=float(ha_value_dec),
                ha_value_str=str(ha_value_dec),
            )
        )
    return readings


def build_mqtt_client(settings: Settings, serial: str | None) -> mqtt.Client:
    client = mqtt.Client(
        client_id=settings.mqtt_client_id
        or f"pykmp-ha-{serial or os.uname().nodename}"
    )
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    client.enable_logger(LOGGER)
    client.reconnect_delay_set(min_delay=5, max_delay=120)
    client.connect(settings.mqtt_host, port=settings.mqtt_port, keepalive=60)
    client.loop_start()
    return client


def publish_discovery(
    client: mqtt.Client,
    *,
    settings: Settings,
    serial: str | None,
    readings: Iterable[RegisterReading],
) -> None:
    if not settings.mqtt_discovery:
        return
    if not serial:
        LOGGER.info("Skipping MQTT discovery because meter serial is unknown.")
        return

    device = {
        "identifiers": [f"pykmp_{serial}"],
        "manufacturer": "Kamstrup",
        "model": "MULTICAL",
        "name": f"Kamstrup meter {serial}",
    }
    for reading in readings:
        unique_id = f"pykmp_{serial}_{reading.id_}"
        config_topic = (
            f"{settings.mqtt_discovery_prefix}/sensor/{unique_id}/config"
        )
        state_topic = f"{settings.mqtt_base_topic}/register/{reading.id_}"
        device_class, state_class = HA_CLASS_BY_UNIT.get(reading.ha_unit, (None, None))
        payload = {
            "name": f"{reading.name}",
            "state_topic": state_topic,
            "value_template": "{{ value_json.value }}",
            "unit_of_measurement": reading.ha_unit,
            "unique_id": unique_id,
            "device": device,
            "expire_after": settings.interval_seconds * 2,
        }
        if device_class:
            payload["device_class"] = device_class
        if state_class:
            payload["state_class"] = state_class
        client.publish(
            config_topic,
            json.dumps(payload),
            retain=True,
        )


def publish_serial(
    client: mqtt.Client, *, settings: Settings, serial: str | None
) -> None:
    payload = {"serial": serial, "timestamp": datetime.now(timezone.utc).isoformat()}
    client.publish(
        f"{settings.mqtt_base_topic}/serial",
        json.dumps(payload),
        retain=settings.mqtt_retain,
    )


def publish_registers(
    client: mqtt.Client,
    *,
    settings: Settings,
    serial: str | None,
    readings: Sequence[RegisterReading],
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    summary = {
        str(reading.id_): {
            "value": reading.ha_value,
            "text": reading.ha_value_str,
            "unit": reading.ha_unit,
            "raw_value": reading.value,
            "raw_text": reading.text,
            "raw_unit": reading.unit,
        }
        for reading in readings
    }
    register_data_payload = [
        {
            "id_int": reading.id_,
            "id_hex": reading.id_hex,
            "name": reading.name,
            "unit_int": reading.unit_int,
            "unit_hex": reading.unit_hex,
            "unit_str": reading.unit,
            "value_float": reading.value,
            "value_str": reading.text,
            "unit_of_measurement": reading.unit,
            "device_class": HA_CLASS_BY_UNIT.get(reading.ha_unit, (None, None))[0],
            "state_class": HA_CLASS_BY_UNIT.get(reading.ha_unit, (None, None))[1],
            "ha_unit": reading.ha_unit,
            "ha_value_float": reading.ha_value,
            "ha_value_str": reading.ha_value_str,
        }
        for reading in readings
    ]
    client.publish(
        f"{settings.mqtt_base_topic}/state",
        json.dumps(
            {
                "serial": serial,
                "timestamp": timestamp,
                "registers": summary,
                "register_data": register_data_payload,
            }
        ),
        retain=settings.mqtt_retain,
    )

    for reading in readings:
        client.publish(
            f"{settings.mqtt_base_topic}/register/{reading.id_}",
            json.dumps(
                {
                    "serial": serial,
                    "timestamp": timestamp,
                    "id": reading.id_,
                    "id_hex": reading.id_hex,
                    "name": reading.name,
                    "unit": reading.ha_unit,
                    "unit_int": reading.unit_int,
                    "unit_hex": reading.unit_hex,
                    "unit_of_measurement": reading.ha_unit,
                    "device_class": HA_CLASS_BY_UNIT.get(reading.ha_unit, (None, None))[0],
                    "state_class": HA_CLASS_BY_UNIT.get(reading.ha_unit, (None, None))[1],
                    "value": reading.ha_value,
                    "value_float": reading.ha_value,
                    "value_str": reading.ha_value_str,
                    "text": reading.ha_value_str,
                    "raw_value": reading.value,
                    "raw_value_str": reading.text,
                    "raw_unit": reading.unit,
                }
            ),
            retain=settings.mqtt_retain,
        )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings.from_env()

    stop = False

    def _stop_handler(signum: int, frame: object | None) -> None:
        nonlocal stop
        stop = True
        LOGGER.info("Received signal %s; stopping.", signum)

    signal.signal(signal.SIGTERM, _stop_handler)
    signal.signal(signal.SIGINT, _stop_handler)

    serial = read_serial(settings)
    mqtt_client = build_mqtt_client(settings, serial)
    try:
        publish_serial(mqtt_client, settings=settings, serial=serial)
        discovery_sent = False

        while not stop:
            readings = read_registers(settings)
            if readings:
                publish_registers(
                    mqtt_client, settings=settings, serial=serial, readings=readings
                )
                if not discovery_sent:
                    publish_discovery(
                        mqtt_client,
                        settings=settings,
                        serial=serial,
                        readings=readings,
                    )
                    discovery_sent = True
            time.sleep(settings.interval_seconds)
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
