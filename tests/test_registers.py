# SPDX-FileCopyrightText: 2026 Jan Kundrát <jkt@jankundrat.com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest
import decimal

from pykmp import messages, registers

@pytest.mark.parametrize(
    ("id_", "unit", "blob_with_size", "value_str", "value_dec", "unit_str"),
    [
        pytest.param(
            1001,
            51,
            '04 00 00 00 00 00',
            '0',
            decimal.Decimal('0'),
            'no unit (number)',
        ),
        pytest.param(
            60,
            8,
            '04 43 00 05 c4 a6',
            '378.022',
            decimal.Decimal('378.022'),
            'GJ',
        ),
        pytest.param(
            1002,
            47,
            '04 00 00 00 00 04',
            '00:00:04',
            None,
            'hh:mm:ss',
        ),
        pytest.param(
            1003,
            48,
            '04 00 00 03 ae 4f',
            '2024-12-31',
            None,
            'yy:mm:dd',
        ),
        pytest.param(
            0,
            50,
            '04 00 00 03 38',
            '08-24',
            None,
            'mm:dd',
        ),
        pytest.param(
            348,
            79,
            '07 00 00 18 0c 1f 00 00 04',
            '2024-12-31 00:00:04-00:00',
            None,
            'DST YY-MM-DD hh:mm:ss',
        ),
        # FIXME: how to print the DST? This (unadjusted time, and a DST remark at the end) is what the vendor's
        # documentation is using, but the LogView SW actually shows '07 00 3c 1a 04 15 0c 07 1e' as
        # '2026-04-21 13:07:30', i.e., with the DST offset of one hour already added.
        pytest.param(
            348,
            79,
            '07 00 3C 10 06 1E 0E 30 37',
            '2016-06-30 14:48:55+01:00',
            None,
            'DST YY-MM-DD hh:mm:ss',
        ),
        pytest.param(
            254,
            54,
            '0C 00 30 32 4B 35 32 41 43 31 41 37 43 5A',
            '02K52AC1A7CZ',
            None,
            'ASCII',
        ),
    ]
)
def test_register_parsing(id_, unit, blob_with_size, value_str, value_dec, unit_str):
    data = messages.RegisterData(id_=id_, unit=unit, value=bytes.fromhex(blob_with_size))
    parsed = registers.RegisterOutput.from_register_data(data)
    assert parsed.value_str == value_str
    assert parsed.value_dec == value_dec
    assert parsed.unit_str == unit_str


def test_register_pretty_line():
    data = messages.RegisterData(id_=1001, unit=51, value=bytes.fromhex('04 00 00 00 00 00'))
    parsed = registers.RegisterOutput.from_register_data(data)
    for part in ('1001', 'Fabrication No', ' 0 no unit (number)'):
        assert part in parsed.to_pretty_line()
