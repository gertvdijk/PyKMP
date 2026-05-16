# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest.mock
from typing import TYPE_CHECKING, cast

import pytest
import serial
import serial.serialutil
from typing_extensions import assert_type

from pykmp import codec, constants, messages
from pykmp.client import (
    ClientCodec,
    EncodedClientRequest,
    EncodedClientResponse,
    PySerialClientCommunicator,
)

if TYPE_CHECKING:
    import mock_serial.mock_serial  # pyright: ignore[reportMissingTypeStubs]

    from . import util

SOME_DESTINATION_ADDRESS = 0x3A


def test_client_codec_encode(
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        communicator = ClientCodec(
            destination_address=SOME_DESTINATION_ADDRESS,
        )
        encoded = communicator.encode(messages.GetTypeRequest()).physical_bytes
    get_type_request_length = 6
    assert len(encoded) == get_type_request_length
    assert encoded[0] == constants.ByteCode.START_TO_METER.value
    assert encoded[1] == SOME_DESTINATION_ADDRESS


def test_client_codec_decode(
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        communicator = ClientCodec(destination_address=0x3A)
        decoded = communicator.decode(
            frame=EncodedClientResponse(
                request_cls=messages.GetSerialRequest,
                physical_bytes=codec.PhysicalBytes(
                    # GetSerialNo response for destination address 3A
                    bytes.fromhex("40 3A 02 0012D687 9EE0 0D")
                ),
            ),
        )
    assert isinstance(decoded, messages.GetSerialRequest.get_response_type())


def test_client_codec_decode_ack_not_implemented(
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        communicator = ClientCodec(destination_address=SOME_DESTINATION_ADDRESS)
        with pytest.raises(NotImplementedError):
            communicator.decode(
                frame=EncodedClientResponse(
                    physical_bytes=cast(codec.PhysicalBytes, constants.ACK_BYTES),
                    request_cls=messages.GetTypeRequest,
                ),
            )


def test_client_codec_encode_request_typing() -> None:
    communicator = ClientCodec()
    encoded = communicator.encode(messages.GetSerialRequest())
    assert_type(encoded, EncodedClientRequest[messages.GetSerialRequest])


def test_client_codec_decode_response_typing() -> None:
    response_encoded = codec.PhysicalBytes(
        bytes.fromhex("40 3F 02 01234567 E956 0D")  # GetSerialNo response
    )
    communicator = ClientCodec()
    frame = EncodedClientResponse(
        physical_bytes=response_encoded, request_cls=messages.GetSerialRequest
    )
    response = communicator.decode(frame=frame)
    assert_type(response, messages.GetSerialResponse)


@pytest.mark.parametrize(
    ("serial_device_uri"),
    [
        pytest.param("/dev/ttyS0", id="ttyS0"),
        pytest.param("socket://0.0.0.0:1234", id="network socket"),
    ],
)
def test_client_pyserial_communicator_read_write(
    serial_device_uri: str,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    fake_serial = serial.serial_for_url("loop://", timeout=0.001)
    with unittest.mock.patch("serial.serial_for_url") as mocked_func:
        mocked_func.return_value = fake_serial
        with ensure_no_warnings_logged():
            communicator = PySerialClientCommunicator(serial_device=serial_device_uri)
        mocked_func.assert_called_once()

    some_bytes = b"1234"
    some_bytes_with_stop = b"1234" + constants.ByteCode.STOP.value.to_bytes(1, "big")

    fake_serial.write(some_bytes)
    with ensure_no_warnings_logged():
        bytes_read_num = communicator.read(num_bytes=4)
    assert bytes_read_num == some_bytes

    fake_serial.write(some_bytes_with_stop)
    with ensure_no_warnings_logged():
        bytes_read_until_stop = communicator.read()
    assert bytes_read_until_stop == some_bytes_with_stop

    with pytest.raises(TimeoutError), ensure_no_warnings_logged():
        communicator.read()

    other_bytes = b"5678"
    with ensure_no_warnings_logged():
        communicator.write(codec.PhysicalBytes(other_bytes))
    assert fake_serial.read_all() == other_bytes


@pytest.mark.parametrize(
    ("serial_device_uri"),
    [
        pytest.param("/dev/nonexistentdevice", id="non-existent device in /dev"),
        pytest.param("socket://1.2.3.256:1234", id="invalid network socket URI"),
    ],
)
def test_client_pyserial_communicator_nonexistent(
    serial_device_uri: str,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with pytest.raises(serial.serialutil.SerialException), ensure_no_warnings_logged():
        PySerialClientCommunicator(serial_device=serial_device_uri)


def test_client_pyserial_communicator_send_request(
    mock_serial: mock_serial.mock_serial.MockSerial,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    mock_serial.stub(  # pyright: ignore[reportUnknownMemberType]
        receive_bytes=bytes.fromhex("80 3F 02 35E9 0D"),  # GetSerialNo request
        send_bytes=bytes.fromhex("40 3F 02 01234567 E956 0D"),  # GetSerialNo response
    )
    with ensure_no_warnings_logged():
        communicator = PySerialClientCommunicator(serial_device=mock_serial.port)
        communicator.send_request(message=messages.GetSerialRequest())
