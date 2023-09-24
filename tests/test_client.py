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
GET_TYPE_REQUEST_BYTES = codec.PhysicalBytes(b"\x80\x3A\x01\xfa\x7f\x0d")
ANOTHER_DESTINATION_ADDRESS = 0x3F
GET_SERIAL_RESPONSE_BYTES = codec.PhysicalBytes(
    b"\x40\x3A\x02\x00\x12\xd6\x87\x9e\xe0\x0d"
)


def test_client_codec_encode(
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        communicator = ClientCodec(
            destination_address=SOME_DESTINATION_ADDRESS,
        )
        encoded = communicator.encode(messages.GetTypeRequest()).physical_bytes
    assert encoded[0] == constants.ByteCode.START_TO_METER.value
    assert encoded[1] == SOME_DESTINATION_ADDRESS
    assert len(encoded) == len(GET_TYPE_REQUEST_BYTES)


def test_client_codec_decode(
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        communicator = ClientCodec(destination_address=SOME_DESTINATION_ADDRESS)
        decoded = communicator.decode(
            frame=EncodedClientResponse(
                request_cls=messages.GetSerialRequest,
                physical_bytes=GET_SERIAL_RESPONSE_BYTES,
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
    response_encoded = codec.PhysicalBytes(b"\x40\x3F\x02\x01\x23\x45\x67\xE9\x56\x0D")
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
            communicator = PySerialClientCommunicator(
                serial_device=serial_device_uri
            )  # pyright: ignore[reportGeneralTypeIssues]
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
        PySerialClientCommunicator(
            serial_device=serial_device_uri
        )  # pyright: ignore[reportGeneralTypeIssues]


def test_client_pyserial_communicator_send_request(
    mock_serial: mock_serial.mock_serial.MockSerial,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    mock_serial.stub(  # pyright: ignore[reportUnknownMemberType]
        receive_bytes=b"\x80\x3F\x02\x35\xE9\x0D",  # GetSerialNo request
        send_bytes=b"\x40\x3F\x02\x01\x23\x45\x67\xE9\x56\x0D",  # GetSerialNo response
    )
    with ensure_no_warnings_logged():
        communicator = PySerialClientCommunicator(
            serial_device=mock_serial.port
        )  # pyright: ignore[reportGeneralTypeIssues]
        communicator.send_request(message=messages.GetSerialRequest())
