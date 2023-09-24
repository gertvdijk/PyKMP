# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

"""Constants/definitions for the Kamstrup KMP protocol."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping  # pragma: no cover
    from typing import Final  # pragma: no cover


# Decimals of each variable in the GetRegister command request/response (CID=0x10)
REGISTERS: Final[Mapping[int, str]] = {
    0x003C: "Heat Energy (E1)",
    0x0044: "Volume",
    0x004A: "Flow",
    0x0050: "Current Power",
    0x0056: "Temp1",
    0x0057: "Temp2",
    0x0059: "Tempdiff",
    0x0061: "Temp1xm3",
    0x006E: "Temp2xm3",
    0x0071: "Infoevent",
    0x007B: "MaxFlowDate_Y",
    0x007C: "MaxFlow_Y",
    0x007D: "MinFlowDate_Y",
    0x007E: "MinFlow_Y",
    0x007F: "MaxPowerDate_Y",
    0x0080: "MaxPower_Y",
    0x0081: "MinPowerDate_Y",
    0x0082: "MinPower_Y",
    0x008A: "MaxFlowDate_M",
    0x008B: "MaxFlow_M",
    0x008C: "MinFlowDate_M",
    0x008D: "MinFlow_M",
    0x008E: "MaxPowerDate_M",
    0x008F: "MaxPower_M",
    0x0090: "MinPowerDate_M",
    0x0091: "MinPower_M",
    0x0092: "AvgTemp1_Y",
    0x0093: "AvgTemp2_Y",
    0x0095: "AvgTemp1_M",
    0x0096: "AvgTemp2_M",
    0x010A: "E1HighRes",
    0x03EC: "HourCounter",
}


UNITS_NAMES: Final[Mapping[int, str]] = {
    0x00: "no unit (number)",
    0x01: "Wh",
    0x02: "kWh",
    0x03: "MWh",
    0x04: "GWh",
    0x05: "J",
    0x06: "kJ",
    0x07: "MJ",
    0x08: "GJ",
    0x09: "Cal",
    0x0A: "kCal",
    0x0B: "Mcal",
    0x0C: "Gcal",
    0x0D: "varh",
    0x0E: "kvarh",
    0x0F: "Mvarh",
    0x10: "Gvarh",
    0x11: "VAh",
    0x12: "kVAh",
    0x13: "MVAh",
    0x14: "GVAh",
    0x15: "kW",
    0x16: "kW",
    0x17: "MW",
    0x18: "GW",
    0x19: "kvar",
    0x1A: "kvar",
    0x1B: "Mvar",
    0x1C: "Gvar",
    0x1D: "VA",
    0x1E: "kVA",
    0x1F: "MVA",
    0x20: "GVA",
    0x21: "V",
    0x22: "A",
    0x23: "kV",
    0x24: "kA",
    0x25: "°C",
    0x26: "°K",
    0x27: "l",
    0x28: "m³",
    0x29: "l/h",
    0x2A: "m³/h",
    0x2B: "m³\N{MULTIPLICATION SIGN}C",
    0x2C: "ton",
    0x2D: "ton/h",
    0x2E: "h",
    0x2F: "hh:mm:ss",
    0x30: "yy:mm:dd",
    0x31: "yyyy:mm:dd",
    0x32: "mm:dd",
    0x33: "no unit (number)",
    0x34: "bar",
    0x35: "RTC",
    0x36: "ASCII",
    0x37: "m³ \N{MULTIPLICATION SIGN}10",
    0x38: "ton \N{MULTIPLICATION SIGN}10",
    0x39: "GJ \N{MULTIPLICATION SIGN}10",
    0x3A: "minutes",
    0x3B: "Bitfield",
    0x3C: "s",
    0x3D: "ms",
    0x3E: "days",
    0x3F: "RTC-Q",
    0x40: "Datetime",
}


@enum.unique
class ByteCode(enum.Enum):
    """Special byte values on the physical layer."""

    START_FROM_METER = 0x40
    START_TO_METER = 0x80
    STOP = 0x0D
    ACK = 0x06
    STUFFING = 0x1B


@enum.unique
class DestinationAddress(enum.Enum):
    """Data link layer address."""

    HEAT_METER = 0x3F
    LOGGER_TOP = 0x7F
    LOGGER_BASE = 0xBF


ACK_BYTES: Final[bytes] = ByteCode.ACK.value.to_bytes(1, "big")


@enum.unique
class CommandId(enum.Enum):
    """CID values for messages."""

    GET_TYPE = 0x01
    GET_SERIAL = 0x02
    SET_CLOCK = 0x09
    GET_REGISTER = 0x10
    PUT_REGISTER = 0x11
    GET_EVENT_STATUS = 0x9B
    CLEAR_EVENT_STATUS = 0x9C
    GET_LOG_TIME_PRESENT = 0xA0
    GET_LOG_PAST_PRESENT = 0xA1
    GET_LOG_ID_PRESENT = 0xA2
    GET_LOG_TIME_PAST = 0xA3
