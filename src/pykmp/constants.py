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


# Register display names as used with GetRegister command request/response (CID=0x10)
REGISTERS: Final[Mapping[int, str]] = {
    60: "Heat Energy (E1)",
    68: "Volume",
    74: "Flow",
    80: "Current Power",
    86: "Temp1",
    87: "Temp2",
    89: "Tempdiff",
    97: "Temp1xm3",
    110: "Temp2xm3",
    113: "Infoevent",
    123: "MaxFlowDate_Y",
    124: "MaxFlow_Y",
    125: "MinFlowDate_Y",
    126: "MinFlow_Y",
    127: "MaxPowerDate_Y",
    128: "MaxPower_Y",
    129: "MinPowerDate_Y",
    130: "MinPower_Y",
    138: "MaxFlowDate_M",
    139: "MaxFlow_M",
    140: "MinFlowDate_M",
    141: "MinFlow_M",
    142: "MaxPowerDate_M",
    143: "MaxPower_M",
    144: "MinPowerDate_M",
    145: "MinPower_M",
    146: "AvgTemp1_Y",
    147: "AvgTemp2_Y",
    149: "AvgTemp1_M",
    150: "AvgTemp2_M",
    266: "E1HighRes",
    1004: "HourCounter",
}


UNITS_NAMES: Final[Mapping[int, str]] = {
    0: "no unit (number)",
    1: "Wh",
    2: "kWh",
    3: "MWh",
    4: "GWh",
    5: "J",
    6: "kJ",
    7: "MJ",
    8: "GJ",
    9: "Cal",
    10: "kCal",
    11: "Mcal",
    12: "Gcal",
    13: "varh",
    14: "kvarh",
    15: "Mvarh",
    16: "Gvarh",
    17: "VAh",
    18: "kVAh",
    19: "MVAh",
    20: "GVAh",
    21: "kW",
    22: "kW",
    23: "MW",
    24: "GW",
    25: "kvar",
    26: "kvar",
    27: "Mvar",
    28: "Gvar",
    29: "VA",
    30: "kVA",
    31: "MVA",
    32: "GVA",
    33: "V",
    34: "A",
    35: "kV",
    36: "kA",
    37: "°C",
    38: "K",
    39: "l",
    40: "m³",
    41: "l/h",
    42: "m³/h",
    43: "m³\N{MULTIPLICATION SIGN}C",
    44: "ton",
    45: "ton/h",
    46: "h",
    47: "hh:mm:ss",
    48: "yy:mm:dd",
    49: "yyyy:mm:dd",
    50: "mm:dd",
    51: "no unit (number)",
    52: "bar",
    53: "RTC",
    54: "ASCII",
    55: "m³ \N{MULTIPLICATION SIGN}10",
    56: "ton \N{MULTIPLICATION SIGN}10",
    57: "GJ \N{MULTIPLICATION SIGN}10",
    58: "minutes",
    59: "Bitfield",
    60: "s",
    61: "ms",
    62: "days",
    63: "RTC-Q",
    64: "Datetime",
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
