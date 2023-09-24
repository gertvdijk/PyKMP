# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import ClassVar

import pytest

from pykmp import codec, constants
from pykmp.messages import (
    BaseRequest,
    BaseResponse,
    DataWithNoDataError,
    GetRegisterRequest,
    GetRegisterResponse,
    GetSerialRequest,
    GetSerialResponse,
    GetTypeRequest,
    GetTypeResponse,
    HasCommandIdAndName,
    MessageCidMismatchError,
    RegisterData,
    RegisterID,
    RegisterUnit,
    RegisterValueBytes,
    SerialNumberInvalidError,
    SoftwareRevisionInvalidError,
)

from . import util

EMPTY_DATA = codec.ApplicationDataBytes(b"")


def _wrong_command_id_msg(*, cid_sent: int, cmd_cls: type[HasCommandIdAndName]) -> str:
    return (
        f"Expected Command ID {cmd_cls.command_id} for {cmd_cls.__name__}, "
        f"got {cid_sent}."
    )


def test_messages_get_sibling_type(
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    class FooRequest(BaseRequest["FooResponse"]):
        response_type: ClassVar[type]
        command_id: ClassVar[int] = 123
        command_name: ClassVar[str] = "Foo"

    class FooResponse(BaseResponse[FooRequest]):
        request_type: ClassVar = FooRequest
        command_id: ClassVar[int] = 123
        command_name: ClassVar[str] = "Foo"

    FooRequest.response_type = FooResponse

    with ensure_no_warnings_logged():
        assert FooRequest.get_response_type() == FooResponse
        assert FooResponse.get_request_type() == FooRequest


def test_messages_get_type_request(
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        data = codec.ApplicationData(
            command_id=constants.CommandId.GET_TYPE.value,
            data=EMPTY_DATA,
        )
        request = GetTypeRequest.decode(data=data)
        assert request == GetTypeRequest()
        assert request.encode() == data


@pytest.mark.parametrize(
    ("command_id", "data_raw", "exc_type", "exc_message"),
    [
        pytest.param(
            constants.CommandId.GET_TYPE.value,
            codec.ApplicationDataBytes(b"foo"),
            DataWithNoDataError,
            f"{GetTypeRequest.__name__} does not take any data.",
            id="data not accepted",
        ),
        pytest.param(
            constants.CommandId.GET_REGISTER.value,
            codec.ApplicationDataBytes(b""),
            MessageCidMismatchError,
            _wrong_command_id_msg(
                cid_sent=constants.CommandId.GET_REGISTER.value,
                cmd_cls=GetTypeRequest,
            ),
            id="wrong command ID",
        ),
    ],
)
def test_messages_get_type_request_decode_error(
    command_id: int,
    data_raw: codec.ApplicationDataBytes,
    exc_type: type,
    exc_message: str,
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        GetTypeRequest.decode(
            data=codec.ApplicationData(
                command_id=command_id,
                data=data_raw,
            )
        )


@pytest.mark.parametrize(
    ("app_bytes", "expected_meter_bytes", "expected_sw_rev"),
    [
        pytest.param(
            codec.ApplicationDataBytes(b"\x00\x04\x06\x01"),
            b"\x00\x04",
            "F1",
            id="Kamstrup doc 6.2.1 GetType response",
        ),
        pytest.param(
            codec.ApplicationDataBytes(b"\x00\x04\x01\x00"),
            b"\x00\x04",
            "A0",
            id="software revision min",
        ),
        pytest.param(
            codec.ApplicationDataBytes(b"\x00\x04\x1a\xFF"),
            b"\x00\x04",
            "Z255",
            id="software revision max",
        ),
        pytest.param(
            codec.ApplicationDataBytes(b"\x00\x04\x00\x00"),
            b"\x00\x04",
            None,
            id="software revision unavailable",
        ),
    ],
)
def test_messages_get_type_response(
    app_bytes: codec.ApplicationDataBytes,
    expected_meter_bytes: bytes,
    expected_sw_rev: str | None,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        data = codec.ApplicationData(
            command_id=constants.CommandId.GET_TYPE.value,
            data=app_bytes,
        )
        response = GetTypeResponse.decode(data=data)
        assert response == GetTypeResponse(
            meter_type_bytes=expected_meter_bytes,
            software_revision=expected_sw_rev,
            data_raw=app_bytes,
        )
        assert response.encode() == data


@pytest.mark.parametrize(
    ("command_id", "data_raw", "exc_type", "exc_message"),
    [
        pytest.param(
            constants.CommandId.GET_TYPE.value,
            codec.ApplicationDataBytes(b"\x00\x00\x04\x06\x01"),
            codec.DataLengthUnexpectedError,
            "GetType response data is of length 5, expected length is 4.",
            id="data longer than 32 bits",
        ),
        pytest.param(
            constants.CommandId.GET_TYPE.value,
            codec.ApplicationDataBytes(b"\x04\x06\x01"),
            codec.DataLengthUnexpectedError,
            "GetType response data is of length 3, expected length is 4.",
            id="data shorter than 32 bits",
        ),
        pytest.param(
            constants.CommandId.GET_TYPE.value,
            codec.ApplicationDataBytes(b""),
            codec.DataLengthUnexpectedError,
            "GetType response data is of length 0, expected length is 4.",
            id="data missing",
        ),
        pytest.param(
            constants.CommandId.GET_TYPE.value,
            codec.ApplicationDataBytes(b"\x00\x04\x1B\x01"),
            codec.OutOfRangeError,
            "Software revision letter (int value) is out of range [1,26]: 27.",
            id="software revision letter out of range (over)",
        ),
        pytest.param(
            constants.CommandId.GET_TYPE.value,
            codec.ApplicationDataBytes(b"\x00\x04\x00\x01"),
            codec.OutOfRangeError,
            "Software revision letter (int value) is out of range [1,26]: 0.",
            id="software revision letter out of range (under)",
        ),
        pytest.param(
            constants.CommandId.GET_REGISTER.value,
            codec.ApplicationDataBytes(b"\x01\x23\x45\x67"),
            MessageCidMismatchError,
            _wrong_command_id_msg(
                cid_sent=constants.CommandId.GET_REGISTER.value,
                cmd_cls=GetTypeResponse,
            ),
            id="wrong command ID",
        ),
    ],
)
def test_messages_get_type_response_decode_error(
    command_id: int,
    data_raw: codec.ApplicationDataBytes,
    exc_type: type,
    exc_message: str,
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        GetTypeResponse.decode(
            data=codec.ApplicationData(
                command_id=command_id,
                data=data_raw,
            )
        )


@pytest.mark.parametrize(
    ("software_revision"),
    [
        pytest.param("FF", id="not a number"),
        pytest.param("F256", id="number out of range"),
        pytest.param("a1", id="letter out of range"),
    ],
)
def test_messages_get_type_response_encode_error_software_revision(
    software_revision: str,
) -> None:
    with pytest.raises(
        SoftwareRevisionInvalidError,
        match=util.full_match_re(
            f"Software revision string {software_revision!r} is invalid."
        ),
    ):
        GetTypeResponse(
            meter_type_bytes=b"\x00\x00", software_revision=software_revision
        ).encode()


@pytest.mark.parametrize(
    ("meter_type_bytes", "exc_message"),
    [
        pytest.param(
            b"\x00\x00\x00",
            "GetTypeResponse meter type bytes is of length 3, expected length is 2.",
            id="too long",
        ),
        pytest.param(
            b"\x00",
            "GetTypeResponse meter type bytes is of length 1, expected length is 2.",
            id="too short",
        ),
    ],
)
def test_messages_get_type_response_encode_error_meter_type_bytes(
    meter_type_bytes: bytes,
    exc_message: str,
) -> None:
    with pytest.raises(
        codec.DataLengthUnexpectedError, match=util.full_match_re(exc_message)
    ):
        GetTypeResponse(
            meter_type_bytes=meter_type_bytes, software_revision="F1"
        ).encode()


def test_messages_get_serial_request(
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        data = codec.ApplicationData(
            command_id=constants.CommandId.GET_SERIAL.value,
            data=EMPTY_DATA,
        )
        request = GetSerialRequest.decode(data=data)
        assert request == GetSerialRequest()
        assert request.encode() == data


@pytest.mark.parametrize(
    ("command_id", "data_raw", "exc_type", "exc_message"),
    [
        pytest.param(
            constants.CommandId.GET_SERIAL.value,
            codec.ApplicationDataBytes(b"foo"),
            DataWithNoDataError,
            f"{GetSerialRequest.__name__} does not take any data.",
            id="data not accepted",
        ),
        pytest.param(
            constants.CommandId.GET_REGISTER.value,
            EMPTY_DATA,
            MessageCidMismatchError,
            _wrong_command_id_msg(
                cid_sent=constants.CommandId.GET_REGISTER.value,
                cmd_cls=GetSerialRequest,
            ),
            id="wrong command ID",
        ),
    ],
)
def test_messages_get_serial_request_decode_error(
    command_id: int,
    data_raw: codec.ApplicationDataBytes,
    exc_type: type,
    exc_message: str,
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        GetSerialRequest.decode(
            data=codec.ApplicationData(
                command_id=command_id,
                data=data_raw,
            )
        )


@pytest.mark.parametrize(
    ("app_bytes", "expected_serial"),
    [
        pytest.param(
            codec.ApplicationDataBytes(b"\x01\x23\x45\x67"),
            "19088743",
            id="serial-0x01234567",
        ),
        pytest.param(
            codec.ApplicationDataBytes(b"\x00\x00\x00\x00"),
            "0",
            id="serial-0x00000000",
        ),
        pytest.param(
            codec.ApplicationDataBytes(b"\xFF\xFF\xFF\xFF"),
            str(2**32 - 1),
            id="serial-0xFFFFFFFF",
        ),
    ],
)
def test_messages_get_serial_response(
    app_bytes: codec.ApplicationDataBytes,
    expected_serial: str,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        data = codec.ApplicationData(
            command_id=constants.CommandId.GET_SERIAL.value,
            data=app_bytes,
        )
        response = GetSerialResponse.decode(data=data)
        assert response == GetSerialResponse(serial=expected_serial, data_raw=app_bytes)
        assert response.encode() == data


@pytest.mark.parametrize(
    ("command_id", "data_raw", "exc_type", "exc_message"),
    [
        pytest.param(
            constants.CommandId.GET_SERIAL.value,
            codec.ApplicationDataBytes(b"\x01\x23\x45\x67\x89"),
            codec.DataLengthUnexpectedError,
            "Serial data is of length 5, expected length is 4.",
            id="serial longer than 32 bits",
        ),
        pytest.param(
            constants.CommandId.GET_SERIAL.value,
            codec.ApplicationDataBytes(b"\x01\x23\x45"),
            codec.DataLengthUnexpectedError,
            "Serial data is of length 3, expected length is 4.",
            id="serial shorter than 32 bits",
        ),
        pytest.param(
            constants.CommandId.GET_SERIAL.value,
            EMPTY_DATA,
            codec.DataLengthUnexpectedError,
            "Serial data is of length 0, expected length is 4.",
            id="data missing",
        ),
        pytest.param(
            constants.CommandId.GET_REGISTER.value,
            codec.ApplicationDataBytes(b"\x01\x23\x45\x67"),
            MessageCidMismatchError,
            _wrong_command_id_msg(
                cid_sent=constants.CommandId.GET_REGISTER.value,
                cmd_cls=GetSerialResponse,
            ),
            id="wrong command ID",
        ),
    ],
)
def test_messages_get_serial_response_decode_error(
    command_id: int,
    data_raw: codec.ApplicationDataBytes,
    exc_type: type,
    exc_message: str,
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        GetSerialResponse.decode(
            data=codec.ApplicationData(
                command_id=command_id,
                data=data_raw,
            )
        )


@pytest.mark.parametrize(
    ("serial", "exc_type", "exc_message"),
    [
        pytest.param(
            "Foobar",
            SerialNumberInvalidError,
            "Serial 'Foobar' is invalid; should contain digits only.",
            id="serial should be digits",
        ),
        pytest.param(
            str(2**32),
            codec.OutOfRangeError,
            "Serial number is out of range [0,4294967295]: 4294967296.",
            id="serial number out of range [over]",
        ),
        pytest.param(
            "-1",
            codec.OutOfRangeError,
            "Serial number is out of range [0,4294967295]: -1.",
            id="serial number out of range [under]",
        ),
    ],
)
def test_messages_get_serial_response_serial_value_invalid(
    serial: str, exc_type: type, exc_message: str
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        GetSerialResponse(serial=serial)


@pytest.mark.parametrize(
    ("app_bytes", "expected_register_ids"),
    [
        pytest.param(
            codec.ApplicationDataBytes(b"\x01\x00\x80"),
            [128],
            id="Kamstrup doc 6.2.4 GetRegister request",
        ),
        pytest.param(
            codec.ApplicationDataBytes(
                b"\x08\x00\x36\x00\x37\x00\x38\x00\x39\x00\x3A\x00\x3B\x00\x3C\x00\x3D"
            ),
            [54, 55, 56, 57, 58, 59, 60, 61],
            id="max number (8) of registers",
        ),
    ],
)
def test_messages_get_register_request(
    app_bytes: codec.ApplicationDataBytes,
    expected_register_ids: list[int],
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        data = codec.ApplicationData(
            command_id=constants.CommandId.GET_REGISTER.value,
            data=app_bytes,
        )
        request = GetRegisterRequest.decode(data=data)
        assert request == GetRegisterRequest(
            registers=expected_register_ids, data_raw=app_bytes
        )
        assert request.encode() == data


@pytest.mark.parametrize(
    ("command_id", "data_raw", "exc_type", "exc_message"),
    [
        pytest.param(
            constants.CommandId.GET_REGISTER.value,
            codec.ApplicationDataBytes(b"\x01"),
            codec.DataLengthUnexpectedError,
            (
                "GetRegister request data for 1 register ID(s) is of length 0, "
                "expected length is 2."
            ),
            id="wrong length byte (no register IDs)",
        ),
        pytest.param(
            constants.CommandId.GET_REGISTER.value,
            codec.ApplicationDataBytes(b"\x03\x00\x36\x00\x37"),
            codec.DataLengthUnexpectedError,
            (
                "GetRegister request data for 3 register ID(s) is of length 4, "
                "expected length is 6."
            ),
            id="wrong length byte",
        ),
        pytest.param(
            constants.CommandId.GET_REGISTER.value,
            EMPTY_DATA,
            codec.DataLengthUnexpectedError,
            "GetRegister request data is of length 0, expected length is 1 at minimum.",
            id="empty",
        ),
        pytest.param(
            constants.CommandId.GET_SERIAL.value,
            codec.ApplicationDataBytes(b"\x01\x23\x45\x67"),
            MessageCidMismatchError,
            _wrong_command_id_msg(
                cid_sent=constants.CommandId.GET_SERIAL.value,
                cmd_cls=GetRegisterRequest,
            ),
            id="wrong command ID",
        ),
    ],
)
def test_messages_get_register_request_decode_error(
    command_id: int,
    data_raw: codec.ApplicationDataBytes,
    exc_type: type,
    exc_message: str,
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        GetRegisterRequest.decode(
            data=codec.ApplicationData(
                command_id=command_id,
                data=data_raw,
            )
        )


@pytest.mark.parametrize(
    ("data_raw", "expected_log_message"),
    [
        pytest.param(
            codec.ApplicationDataBytes(b"\x00"),
            (
                "Number of registers (0) in GetRegister request is outside the defined "
                "range (1-8)."
            ),
            id="zero length",
        ),
        pytest.param(
            codec.ApplicationDataBytes(
                b"\x09\x00\x36\x00\x37\x00\x38\x00\x39\x00\x3A\x00\x3B\x00\x3C\x00\x3D"
                b"\x00\x3E"
            ),
            (
                "Number of registers (9) in GetRegister request is outside the defined "
                "range (1-8)."
            ),
            id="length over range",
        ),
    ],
)
def test_messages_get_register_request_decode_length_out_of_range_warning(
    data_raw: codec.ApplicationDataBytes,
    expected_log_message: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        request = GetRegisterRequest.decode(
            data=codec.ApplicationData(
                command_id=constants.CommandId.GET_REGISTER.value,
                data=data_raw,
            )
        )
    expected_num_registers = data_raw[0]
    assert len(request.registers) == expected_num_registers
    logs = [rec.message for rec in caplog.records if rec.levelno >= logging.WARNING]
    assert logs == [expected_log_message]


NUM_REGISTERS_MAX = GetRegisterRequest.NUM_REGISTERS_MAX


@pytest.mark.parametrize(
    ("registers", "exc_type", "exc_message"),
    [
        pytest.param(
            [],
            codec.OutOfRangeError,
            (
                "Number of registers requested in GetRegister request is out of range "
                "[1,8]: 0."
            ),
            id="empty",
        ),
        pytest.param(
            list(range(NUM_REGISTERS_MAX + 1)),
            codec.OutOfRangeError,
            (
                "Number of registers requested in GetRegister request is out of range "
                f"[1,{NUM_REGISTERS_MAX}]: {NUM_REGISTERS_MAX+1}."
            ),
            id="too many",
        ),
    ],
)
def test_messages_get_register_request_encode_error(
    registers: list[int],
    exc_type: type,
    exc_message: str,
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        GetRegisterRequest(registers=registers).encode()


@pytest.mark.parametrize(
    ("registers", "exc_type", "exc_message"),
    [
        pytest.param(
            [2 ** (GetRegisterRequest.REGISTER_ID_LENGTH_ENCODED * 8)],
            codec.OutOfRangeError,
            "Register ID is out of range [0,65535]: 65536.",
            id="out of range [over]",
        ),
        pytest.param(
            [-1],
            codec.OutOfRangeError,
            "Register ID is out of range [0,65535]: -1.",
            id="out of range [under]",
        ),
    ],
)
def test_messages_get_register_request_register_value_invalid(
    registers: list[int],
    exc_type: type,
    exc_message: str,
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        GetRegisterRequest(registers=registers)


@pytest.mark.parametrize(
    ("app_bytes", "expected_register_data"),
    [
        pytest.param(
            codec.ApplicationDataBytes(b"\x00\x80\x16\x04\x11\x01\x2A\xF0\x24"),
            {
                RegisterData(
                    id_=RegisterID(128),
                    unit=RegisterUnit(0x16),
                    value=RegisterValueBytes(b"\x04\x11\x01\x2A\xF0\x24"),
                ),
            },
            id="Kamstrup doc 6.2.4 GetRegister response",
        ),
        pytest.param(
            EMPTY_DATA,
            {},
            id="empty is valid (ie. no register IDs in request recognized)",
        ),
    ],
)
def test_messages_get_register_response(
    app_bytes: codec.ApplicationDataBytes,
    expected_register_data: set[RegisterData],
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        data = codec.ApplicationData(
            command_id=constants.CommandId.GET_REGISTER.value,
            data=app_bytes,
        )
        response = GetRegisterResponse.decode(data=data)

        expected_registers: dict[RegisterID, RegisterData] = {
            r.id_: r for r in expected_register_data
        }
        assert response == GetRegisterResponse(
            registers=expected_registers, data_raw=app_bytes
        )
        assert response.encode() == data


@pytest.mark.parametrize(
    ("command_id", "app_bytes", "exc_type", "exc_message"),
    [
        pytest.param(
            constants.CommandId.GET_REGISTER.value,
            codec.ApplicationDataBytes(b"\x00\x80\x16\x04\x11\x01\x2A\xF0"),
            codec.DataLengthUnexpectedError,
            (
                "Register value data left in buffer is of length 8, expected length is "
                "9 at minimum."
            ),
            id="truncated by one byte",
        ),
        pytest.param(
            constants.CommandId.GET_REGISTER.value,
            codec.ApplicationDataBytes(b"\x00\x80\x16\x04\x11"),
            codec.DataLengthUnexpectedError,
            (
                "Data to decode register data is of length 5, expected length is 6 at "
                "minimum."
            ),
            id="too short",
        ),
        pytest.param(
            constants.CommandId.GET_REGISTER.value,
            codec.ApplicationDataBytes(b"\x00\x80\x16\x04\x11\x01\x2A\xF0\x24\x01"),
            codec.DataLengthUnexpectedError,
            (
                "Data to decode register data is of length 1, expected length is 6 at "
                "minimum."
            ),
            id="superfluous data after full register data",
        ),
        pytest.param(
            constants.CommandId.GET_SERIAL.value,
            codec.ApplicationDataBytes(b"\x01\x23\x45\x67"),
            MessageCidMismatchError,
            _wrong_command_id_msg(
                cid_sent=constants.CommandId.GET_SERIAL.value,
                cmd_cls=GetRegisterResponse,
            ),
            id="wrong command ID",
        ),
    ],
)
def test_messages_get_register_response_decode_error(
    command_id: int,
    app_bytes: codec.ApplicationDataBytes,
    exc_type: type,
    exc_message: str,
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        GetRegisterResponse.decode(
            data=codec.ApplicationData(
                command_id=command_id,
                data=app_bytes,
            )
        )


@pytest.mark.parametrize(
    ("app_bytes", "expected_register_data", "expected_log_message"),
    [
        pytest.param(
            codec.ApplicationDataBytes(b"\x00\x80\x16\x04\x11\x01\x2A\xF0\x24" * 2),
            {
                RegisterData(
                    id_=RegisterID(128),
                    unit=RegisterUnit(0x16),
                    value=RegisterValueBytes(b"\x04\x11\x01\x2A\xF0\x24"),
                ),
            },
            "Duplicate register ID 128 in response, overwriting value.",
            id="duplicate register ID",
        ),
    ],
)
def test_messages_get_register_response_decode_warning(
    app_bytes: codec.ApplicationDataBytes,
    expected_register_data: set[RegisterData],
    expected_log_message: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        response = GetRegisterResponse.decode(
            data=codec.ApplicationData(
                command_id=constants.CommandId.GET_REGISTER.value,
                data=app_bytes,
            )
        )
    expected_registers: dict[RegisterID, RegisterData] = {
        r.id_: r for r in expected_register_data
    }
    assert response.registers == expected_registers
    logs = [rec.message for rec in caplog.records if rec.levelno >= logging.WARNING]
    assert logs == [expected_log_message]
