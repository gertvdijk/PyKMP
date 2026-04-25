# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
# SPDX-FileCopyrightText: 2026 Jan Kundrát <jkt@jankundrat.com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from pykmp import messages
from pykmp.client import (
    ClientCodec,
    UnknownCidError,
)

SOME_DESTINATION_ADDRESS = 0x3A
ANOTHER_DESTINATION_ADDRESS = 0x3F


@pytest.mark.parametrize(
    ("payload", "parsed"),
    [
        pytest.param(
            '80 3f 01 05 8a 0d',
            messages.GetTypeRequest(),
        ),
        pytest.param(
            '80 3f 02 35 e9 0d',
            messages.GetSerialRequest(),
        ),
        pytest.param(
            '80 3f 10 02 01 5a 00 9a 1b bf 2b 0d',
            messages.GetRegisterRequest(data_raw=bytes.fromhex('02 01 5A 00 9a'), registers=[346, 154]),
        ),
        pytest.param(
            '80 3f 10 01 03 e9 7c d4 0d',
            messages.GetRegisterRequest(data_raw=bytes.fromhex('01 03 e9'), registers=[1001]),
        ),
        pytest.param(
            '80 ff ff 1d 0f 0d',
            UnknownCidError(cid=0xff, raw_data=b''),
        ),
    ]
)
def test_blind_command_decoding(payload, parsed) -> None:
    communicator = ClientCodec(
        destination_address=ANOTHER_DESTINATION_ADDRESS,
    )
    raw_bytes = bytes.fromhex(payload)
    if isinstance(parsed, Exception):
        with pytest.raises(type(parsed)) as excinfo:
            decoded = communicator.decode_command(raw_bytes)
        assert str(excinfo.value) == str(parsed)
    else:
        decoded = communicator.decode_command(raw_bytes)
        assert decoded == parsed
        encoded = communicator.encode(parsed).physical_bytes
        assert encoded.hex(' ') == payload

@pytest.mark.parametrize(
    ("payload", "parsed"),
    [
        pytest.param(
            '40 3f 10 03 e9 33 04 00 00 00 00 00 63 38 0d',
            messages.GetRegisterResponse(data_raw=bytes.fromhex('03 e9 33 04 00 00 00 00 00'),
                                         registers={1001:
                                                    messages.RegisterData(id_=1001, unit=51,
                                                                          value=bytes.fromhex('04 00 00 00 00 00'))}),
        ),
        pytest.param(
            '06',
            NotImplementedError(),
        ),
        pytest.param(
            '40 ff ff 1d 0f 0d',
            UnknownCidError(cid=0xff, raw_data=b''),
        ),
    ]
)
def test_blind_response_decoding(payload, parsed) -> None:
    communicator = ClientCodec(
        destination_address=SOME_DESTINATION_ADDRESS,
    )
    if isinstance(parsed, Exception):
        with pytest.raises(type(parsed)) as excinfo:
            decoded = communicator.decode_response(bytes.fromhex(payload))
        assert str(excinfo.value) == str(parsed)
    else:
        decoded = communicator.decode_response(bytes.fromhex(payload))
        assert decoded == parsed
