# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import decimal
from typing import Final

import attrs

from . import codec, constants, messages


REGISTERS_NAMES_LEN_MAX: Final[int] = max(
    len(name) for name in constants.REGISTERS.values()
)


@attrs.define(kw_only=True)
class RegisterOutput:
    id_int: int
    id_hex: str = attrs.field(init=False)
    name: str = attrs.field(init=False)
    unit_int: int
    unit_hex: str = attrs.field(init=False)
    unit_str: str = attrs.field(init=False)
    value_float: float = attrs.field(init=False, default=None)
    value_str: str = attrs.field()  # best: uses decimal.Decimal without loss
    value_dec: decimal.Decimal = attrs.field()

    def __attrs_post_init__(self) -> None:
        self.id_hex = f"0x{self.id_int:04X}"
        self.unit_hex = f"0x{self.unit_int:02X}"
        self.name = constants.REGISTERS.get(self.id_int, f"<unknown reg {self.id_int}>")
        self.unit_str = constants.UNITS_NAMES.get(
            self.unit_int, f"<unknown unit {self.unit_int}>"
        )
        if self.value_dec is not None:
            self.value_float = float(self.value_dec)
            self.value_str = str(self.value_dec)

    @classmethod
    def from_register_data(cls, reg: messages.RegisterData) -> Self:
        value_dec = None
        value_str = None
        match reg.unit:
            case 0x2f:
                # hh:mm:ss
                d = int.from_bytes(reg.value[2:], 'big')
                value_str = f'{(d//10000):02}:{(d // 100 % 100):02}:{(d % 100):02}'
                pass
            case 0x30:
                # yy-mm-dd
                d = int.from_bytes(reg.value[2:], 'big')
                value_str = f'{(2000 + d//10000):02}-{(d // 100 % 100):02}-{(d % 100):02}'
                pass
            case 0x32:
                # mm-dd
                d = int.from_bytes(reg.value[2:], 'big')
                value_str = f'{(d // 100 % 100):02}-{(d % 100):02}'
            case 0x4f:
                # DST yy:mm:dd hh:mm:ss
                dst = reg.value[2]
                value_str = f'{(2000 + reg.value[3]):02}-{reg.value[4]:02}-{reg.value[5]:02} ' \
                    + f'{reg.value[6]:02}:{reg.value[7]:02}:{reg.value[8]:02}' \
                    + f'{"+" if dst > 0 else "-"}{(dst // 60):02}:{(dst % 60):02}'
            case 0x36:
                # ASCII
                value_str = bytes(reg.value[2:]).decode('ascii')
            case _:
                value_dec = codec.FloatCodec.decode(reg.value)
        return cls(
            id_int=reg.id_,
            unit_int=reg.unit,
            value_dec=value_dec,
            value_str=value_str,
        )

    def to_pretty_line(self) -> str:
        return (
            f"{self.id_int!r:>4} → {self.name:<{REGISTERS_NAMES_LEN_MAX}} = "
            f"{self.value_str} {self.unit_str}"
        )
