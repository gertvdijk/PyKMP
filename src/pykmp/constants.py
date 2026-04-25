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
    1: "Energy in",
    2: "Energy out",
    13: "Energy in hires",
    14: "Energy out hires",
    60: "Heat Energy (E1)",
    61: "Inlet Energy E4",
    62: "Outlet Energy E5",
    63: "Cooling Energy E3",
    64: "Tariff TA2",
    65: "Tariff TA3",
    66: "Tariff limit 2",
    67: "Tariff limit 3",
    68: "Volume V1",
    69: "Volume V2",
    72: "Mass M1",
    73: "Mass M2",
    74: "Flow V1",
    75: "Flow V2",
    80: "Current Power",
    84: "Pulse input A1",
    85: "Pulse input B1",
    86: "Temp1",
    87: "Temp2",
    88: "Temp3",
    89: "Tempdiff",
    91: "Pressure P1",
    92: "Pressure P2",
    94: "Heat Energy E2",
    95: "Tap water energy E6",
    96: "Tap water energy E7",
    97: "Temp1xm3 E8",  # V1 * t1 (inlet)
    98: "Target Date",
    99: "InfoCode",
    104: "Meter number for VB",
    110: "Temp2xm3 E9",  # V2 * t2 (outlet)
    112: "Customer number 2",  # 8 most-significant digits
    113: "Infoevent",
    114: "Meter number for VA",
    122: "Temp4",
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
    152: "Program number",  # not seen on meters: ABCCCCCC
    153: "Config number 1",  # config no. DDDEE
    154: "Software Checksum 1",
    168: "Config number 2",  # config no. FFGGMN
    175: "Error hour counter",
    178: "Differential energy dE",
    179: "Control energy cE",
    180: "Differential volume dV",
    181: "Control volume cV",
    # 183: looks like a meter S/N on Multical 603
    184: "MbusPriAdrMod1",
    185: "MbusSekAdrMod1",
    218: "MbusPriAdrMod2",
    219: "MbusSekAdrMod2",
    222: "ConfigChangedEventCount",
    224: "Pulse input A2",
    225: "Pulse input B2",
    228: "Config number 3",
    229: "T1_average_autoint",
    230: "T2_average_autoint",
    234: "l/imp for VA",
    235: "l/imp for VB",
    239: "Volume V1 hires",
    241: "MaxFlow_D",
    242: "MinFlow_D",
    243: "Reverse flow V1",
    254: "Type no",
    257: "Pulse value V1",
    258: "Pulse value V2",
    268: "Q\N{LATIN SUBSCRIPT SMALL LETTER P} averaging time",
    # Undocumented (259 and 260), but it matches the info given by Multical 603 in the
    # diagnostics display
    259: "Nominal Q\N{LATIN SUBSCRIPT SMALL LETTER P} V1",
    260: "Nominal Q\N{LATIN SUBSCRIPT SMALL LETTER P} V2",
    266: "E1HighRes",
    267: "Cooling energy E3 hires",
    279: "DIN meter ID",
    292: "Water temperature",
    # FIXME(jkt): Uncertain order (293-295), check them in May 2026 when a first "valid" log entry is made
    293: "Min water temperature monthly",
    294: "Max water temperature monthly",
    295: "Avg water temperature monthly",
    296: "Min water temperature daily",
    297: "Max water temperature daily",
    298: "Avg water temperature daily",
    299: "Meter temperature",
    300: "Min meter temperature monthly",
    301: "Max meter temperature monthly",
    302: "Avg meter temperature monthly",
    303: "Min meter temperature daily",
    304: "Max meter temperature daily",
    305: "Avg meter temperature daily",
    # Documentation for 327-330 doesn't match what a KWM2231 water meter is sending
    327: "Target date 1",
    328: "Target date 2",
    338: "Data quality",
    346: "Module SW rev",
    347: "Customer number",
    348: "Date and Time",  # TODO: unknown unit 79, 28591984415535
    355: "COP Year",
    362: "Tariff TA4",
    364: "Heat energy A1",  # Heat energy with discount A1, t2 < t5 limit
    365: "Heat energy A2",  # Heat energy with surcharge A2, t2 > t5 limit
    366: "T5 limit",
    367: "COP Month",
    368: "Config number 4",
    369: "Info bits",
    371: "COP",
    372: "Power input B1",
    379: "T1 time average day",
    380: "T2 time average day",
    381: "T1 time average hour",
    382: "T2 time average hour",
    383: "Flow V1 max year date",
    384: "Flow V1 min year date",
    385: "Power max year date",
    386: "Power min year date",
    387: "Flow V1 max month date",
    388: "Flow V1 min month date",
    389: "Power max month date",
    390: "Power min month time",
    394: "Config XYZ",
    398: "T1 actual (one decimal)",
    399: "T2 actual (one decimal)",
    400: "T1-T2 (one decimal)",
    404: "Meter Type",
    # register 409: a combination of a bitfield and some duration tracking. Example values:
    # 17184063489: dry 1-8 hrs, meter temperature too high: 9-24 hrs, no consumption: 9-24 hrs
    # 17181966337: dry 1-8 hrs, meter temperature too high: 1-8 hrs, no consumption: 9-24 hrs
    # 17179869185: dry 1-8 hrs, no consumption: 9-24 hrs
    # 8589934593: dry 1-8 hrs, no consumption: 1-8 hrs
    409: "Info hour counter",
    440: "MaxFlow_H",
    445: "MaxFlowDate_D",
    446: "MinFlowDate_D",
    # Seen in the logger. E.g. 128 is "meter temperature too high"
    458: "Info code",
    473: "Energy E10",
    474: "Energy E11",
    477: "T3 time average day",
    478: "T3 time average hour",
    505: "P1 average day",
    506: "P2 average day",
    507: "P1 average hour",
    508: "P2 average hour",
    # Undocumented, but it "looks good" on a fresh meter from 2026
    582: "Maybe battery remaining",
    583: "Accoustic noise last day",
    622: "V1 extra digit",
    # Undocumented, e.g., KWM2231
    640: "Meter type text",
    # Undocumented, but it matches the actual interval on Multical 303
    675: "wM-Bus transmission interval",
    # Undocumented (692-721), but it looks like a histogram readout
    692: "Volume in flow bucket 1",
    697: "Volume in flow bucket 2",
    698: "Volume in flow bucket 3",
    699: "Volume in flow bucket 4",
    700: "Volume in flow bucket 5",
    701: "Volume in flow bucket 6",
    702: "Volume in flow bucket 7",
    703: "Volume in flow bucket 8",
    704: "Volume in flow bucket 9",
    705: "Volume in flow bucket 10",
    706: "Volume in flow bucket 11",
    707: "Volume in flow bucket 12",
    708: "Volume in flow bucket 13",
    709: "Flow bucket 1",
    710: "Flow bucket 2",
    711: "Flow bucket 3",
    712: "Flow bucket 4",
    713: "Flow bucket 5",
    714: "Flow bucket 6",
    715: "Flow bucket 7",
    716: "Flow bucket 8",
    717: "Flow bucket 9",
    718: "Flow bucket 10",
    719: "Flow bucket 11",
    720: "Flow bucket 12",
    721: "Flow bucket 13",
    1001: "Fabrication No",
    1002: "Time",
    1003: "Date",
    1004: "HourCounter",
    1005: "Software edition",
    1010: "Customer number 1",  # 8 least-significant digits
    1023: "Power in",
    1024: "Power out",
    1032: "Operation Mode",
    1054: "Voltage L1",
    1055: "Voltage L2",
    1056: "Voltage L3",
    1076: "Current L1",
    1077: "Current L2",
    1078: "Current L3",
    1080: "Power in L1",
    1081: "Power in L2",
    1082: "Power in L3",
    1344: "Power out L1",
    1345: "Power out L2",
    1346: "Power out L3",
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
    21: "W",
    22: "kW",
    23: "MW",
    24: "GW",
    25: "var",
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
    65: "imp/l",
    66: "l/imp",
    85: "%RH",
    86: "%O\N{SUBSCRIPT TWO}",
    87: "m/s",
    88: "kJ/kg",
    89: "pH",
    90: "g/kg",
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
