# Home Assistant MQTT
<!--
SPDX-FileCopyrightText: 2024 The PyKMP contributors

SPDX-License-Identifier: CC0-1.0
-->

This repository now includes a small helper that pushes Kamstrup meter data to a Home
Assistant MQTT broker using the `pykmp-tool` equivalent API calls.

## Install on Raspberry Pi

1. Create a virtualenv on the Pi (or reuse your existing one) and install the extras
   needed for the CLI and MQTT publishing:

   ```console
   $ python3 -m venv /opt/pykmp/.venv
   $ source /opt/pykmp/.venv/bin/activate
   $ pip install --upgrade pip
   $ pip install ".[tool]" paho-mqtt
   ```

2. Copy the example environment file and fill in the MQTT and serial settings:

   ```console
   $ sudo cp contrib/systemd/pykmp-ha.env.example /etc/pykmp-ha.env
   $ sudoedit /etc/pykmp-ha.env
   ```

   The defaults request registers `60 68 80 74 86 87 266` every 300 seconds (5
   minutes) from `/dev/ttyUSB0`. Set `MQTT_HOST` to your broker address; leave
   `MQTT_DISCOVERY=true` to let Home Assistant auto-discover the sensors.

3. Install the systemd unit and point it at your checkout/venv:

   ```console
   $ sudo cp contrib/systemd/pykmp-ha-mqtt.service /etc/systemd/system/
   $ sudoedit /etc/systemd/system/pykmp-ha-mqtt.service
   ```

   Update `User`/`Group`, `WorkingDirectory` and `ExecStart` if your paths differ, for
   example:

   ```
   WorkingDirectory=/opt/PyKMP
   ExecStart=/opt/pykmp/.venv/bin/python /opt/PyKMP/examples/home_assistant_mqtt.py
   ```

4. Enable and start the service:

   ```console
   $ sudo systemctl daemon-reload
   $ sudo systemctl enable --now pykmp-ha-mqtt.service
   $ sudo systemctl status pykmp-ha-mqtt.service
   ```

Make sure the chosen `User` is allowed to talk to the meter (e.g. a member of the
`dialout` group when using `/dev/ttyUSB0`).

## What gets published

- Serial number once on startup: `<MQTT_BASE_TOPIC>/serial`
- All registers together: `<MQTT_BASE_TOPIC>/state`
  - Per-register states (JSON, retained): `<MQTT_BASE_TOPIC>/register/<id>`
  - MQTT discovery (when `MQTT_DISCOVERY=true`): `homeassistant/sensor/pykmp_<serial>_<id>/config`

The state payload now includes both a compact map and a `register_data` list that mirrors
`pykmp-tool get-register --json`, for example:

```json
{
  "serial": "123456",
  "timestamp": "2024-04-12T12:00:00Z",
  "register_data": [
    {
      "id_int": 60,
      "id_hex": "0x003C",
      "name": "Heat Energy (E1)",
      "device_class": "energy",
      "state_class": "total_increasing",
      "unit_of_measurement": "kWh",
      "unit_int": 2,
      "unit_hex": "0x02",
      "unit_str": "kWh",
      "value_float": 135152.0,
      "value_str": "135152"
    }
  ]
}
```

MQTT discovery payloads now also include `device_class` and `state_class` when the unit
is recognized (e.g., energy, volume, temperature, power, flow).

Home Assistant will create one sensor per register via the discovery payloads. If you
prefer manual sensors, point them at the per-register topics above.
