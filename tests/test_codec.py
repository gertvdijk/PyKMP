# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import decimal
import logging

import pytest

from pykmp import constants
from pykmp.codec import (
    AckReceivedException,
    ApplicationBytes,
    ApplicationCodec,
    ApplicationData,
    ApplicationDataBytes,
    BoundaryByteInvalidError,
    CrcChecksumInvalidError,
    DataLengthUnexpectedError,
    DataLinkBytes,
    DataLinkCodec,
    DataLinkData,
    FloatCodec,
    InvalidDestinationAddressError,
    OutOfRangeError,
    PhysicalBytes,
    PhysicalCodec,
    PhysicalDirection,
    UnsupportedDecimalExponentError,
)

from . import util


@pytest.mark.parametrize(
    ("direction", "frame", "expected"),
    [
        pytest.param(
            PhysicalDirection.FROM_METER,
            PhysicalBytes(b"\x40\x3F\x02\x01\x23\x45\x67\xE9\x56\x0D"),
            DataLinkBytes(b"\x3F\x02\x01\x23\x45\x67\xE9\x56"),
            id="Kamstrup doc 6.2.2 GetSerialNo response (no destuffing needed)",
        ),
        pytest.param(
            PhysicalDirection.FROM_METER,
            PhysicalBytes(
                b"\x40\x3F\x10\x00\x1B\x7F\x16\x04\x11\x01\x2A\xF0\x24\x63\x03\x0D"
            ),
            DataLinkBytes(b"\x3F\x10\x00\x80\x16\x04\x11\x01\x2A\xF0\x24\x63\x03"),
            id="Kamstrup doc 6.2.4 GetRegister response (destuffing needed)",
        ),
    ],
)
def test_codec_physical_decode(
    direction: PhysicalDirection,
    frame: PhysicalBytes,
    expected: DataLinkBytes,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        returned = PhysicalCodec(direction=direction).decode(frame)
    assert returned.hex() == expected.hex()


@pytest.mark.parametrize(
    ("direction"),
    [
        pytest.param(
            PhysicalDirection.FROM_METER,
            id="Kamstrup doc 3.1 ACK byte is without start/stop bytes (FROM_METER)",
        ),
        pytest.param(
            PhysicalDirection.TO_METER,
            id="Kamstrup doc 3.1 ACK byte is without start/stop bytes (TO_METER)",
        ),
    ],
)
def test_codec_physical_decode_ack(
    direction: PhysicalDirection,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with pytest.raises(AckReceivedException), ensure_no_warnings_logged():
        PhysicalCodec(direction=direction).decode(PhysicalBytes(constants.ACK_BYTES))


@pytest.mark.parametrize(
    ("direction", "frame", "exc_type", "exc_message"),
    [
        pytest.param(
            PhysicalDirection.FROM_METER,
            PhysicalBytes(b"\x80\x56\x0D"),
            BoundaryByteInvalidError,
            "Frame expected start byte is 64 (hex: 40), but got 128 (hex: 80)",
            id="wrong start byte (FROM_METER)",
        ),
        pytest.param(
            PhysicalDirection.TO_METER,
            PhysicalBytes(b"\x40\x56\x0D"),
            BoundaryByteInvalidError,
            "Frame expected start byte is 128 (hex: 80), but got 64 (hex: 40)",
            id="wrong start byte (TO_METER)",
        ),
        pytest.param(
            PhysicalDirection.FROM_METER,
            PhysicalBytes(b"\x40\x56"),
            BoundaryByteInvalidError,
            "Frame expected stop byte is 13 (hex: 0D), but got 86 (hex: 56)",
            id="wrong stop byte (FROM_METER)",
        ),
        pytest.param(
            PhysicalDirection.FROM_METER,
            b"",
            DataLengthUnexpectedError,
            "Frame is of zero length.",
            id="empty",
        ),
    ],
)
def test_codec_physical_decode_error(
    direction: PhysicalDirection,
    frame: PhysicalBytes,
    exc_type: type,
    exc_message: str,
) -> None:
    codec = PhysicalCodec(direction=direction)
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        codec.decode(frame)


@pytest.mark.parametrize(
    ("direction", "to_encode", "expected"),
    [
        pytest.param(
            PhysicalDirection.TO_METER,
            DataLinkBytes(b"\x04\x0D\x00\x06"),
            PhysicalBytes(b"\x80\x04\x1B\xF2\x00\x1B\xF9\x0D"),
            id="Kamstrup doc 3.1 Physical layer, plus start/stop byte",
        ),
        pytest.param(
            PhysicalDirection.TO_METER,
            DataLinkBytes(b"\x3F\x01\x05\x8A"),
            PhysicalBytes(b"\x80\x3F\x01\x05\x8A\x0D"),
            id="Kamstrup doc 6.2.1 GetType request (no stuffing needed)",
        ),
        pytest.param(
            PhysicalDirection.TO_METER,
            DataLinkBytes(b"\x3F\x10\x01\x00\x80\xD4\x08"),
            PhysicalBytes(b"\x80\x3F\x10\x01\x00\x1B\x7F\xD4\x08\x0D"),
            id="Kamstrup doc 6.2.4 GetRegister request (stuffing needed)",
        ),
        pytest.param(
            PhysicalDirection.TO_METER,
            DataLinkBytes(constants.ByteCode.STUFFING.value.to_bytes(1, "big")),
            PhysicalBytes(b"\x80\x1B\xE4\x0D"),
            id="stuffing character stuffed",
        ),
        pytest.param(
            PhysicalDirection.FROM_METER,
            DataLinkBytes(b"\x3F"),
            PhysicalBytes(b"\x40\x3F\x0D"),
            id="encode as meter (direction=RECEIVE)",
        ),
    ],
)
def test_codec_physical_encode(
    direction: PhysicalDirection,
    to_encode: DataLinkBytes,
    expected: PhysicalBytes,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        codec = PhysicalCodec(direction=direction)
        assert codec.encode(to_encode).hex() == expected.hex()


@pytest.mark.parametrize(
    ("direction"),
    [
        pytest.param(
            PhysicalDirection.TO_METER,
            id="Kamstrup doc 3.1 ACK byte is without start/stop bytes (TO_METER)",
        ),
        pytest.param(
            PhysicalDirection.FROM_METER,
            id="Kamstrup doc 3.1 ACK byte is without start/stop bytes (FROM_METER)",
        ),
    ],
)
def test_codec_physical_encode_ack(
    direction: PhysicalDirection,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        codec = PhysicalCodec(direction=direction)
        assert codec.encode_ack().hex() == constants.ACK_BYTES.hex()


@pytest.mark.parametrize(
    ("direction", "data_link_bytes", "exc_type", "exc_message"),
    [
        pytest.param(
            PhysicalDirection.FROM_METER,
            DataLinkBytes(b""),
            DataLengthUnexpectedError,
            "Data link bytes is of zero length.",
            id="empty",
        ),
    ],
)
def test_codec_physical_encode_error(
    direction: PhysicalDirection,
    data_link_bytes: DataLinkBytes,
    exc_type: type,
    exc_message: str,
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        PhysicalCodec(direction=direction).encode(data_link_bytes)


@pytest.mark.parametrize(
    ("data_link_bytes", "expected"),
    [
        pytest.param(
            DataLinkBytes(b"\x3F\x02\x01\x23\x45\x67\xE9\x56"),
            DataLinkData(
                destination_address=0x3F,
                application_bytes=ApplicationBytes(b"\x02\x01\x23\x45\x67"),
                crc_value=0xE956,
            ),
            id="Kamstrup doc 6.2.2 GetSerialNo response",
        ),
        pytest.param(
            DataLinkBytes(b"\x3F\x10\x00\x80\x16\x04\x11\x01\x2A\xF0\x24\x63\x03"),
            DataLinkData(
                destination_address=0x3F,
                application_bytes=ApplicationBytes(
                    b"\x10\x00\x80\x16\x04\x11\x01\x2A\xF0\x24"
                ),
                crc_value=0x6303,
            ),
            id="Kamstrup doc 6.2.4 GetRegister response",
        ),
    ],
)
def test_codec_data_link_decode(
    data_link_bytes: DataLinkBytes,
    expected: DataLinkData,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        assert DataLinkCodec().decode(data_link_bytes) == expected


@pytest.mark.parametrize(
    ("data_link_bytes", "exc_type", "exc_message"),
    [
        pytest.param(
            DataLinkBytes(b"\x56"),
            DataLengthUnexpectedError,
            "Data link layer message to destructure is of length 1, expected length "
            "is 4 at minimum.",
            id="too short",
        ),
        pytest.param(
            DataLinkBytes(b""),
            DataLengthUnexpectedError,
            "Data link layer message to destructure is of length 0, expected length "
            "is 4 at minimum.",
            id="empty",
        ),
    ],
)
def test_codec_data_link_decode_error(
    data_link_bytes: DataLinkBytes,
    exc_type: type,
    exc_message: str,
) -> None:
    codec = DataLinkCodec()
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        codec.decode(data_link_bytes)


def test_codec_data_link_decode_checksum_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Kamstrup doc 6.2.2 GetSerialNo response with broken checksum
    broken_data_link_bytes = DataLinkBytes(b"\x3F\x02\x01\x23\x45\x67\xE9\x57")

    codec = DataLinkCodec()
    with pytest.raises(CrcChecksumInvalidError), caplog.at_level(logging.WARNING):
        codec.decode(broken_data_link_bytes)

    warnings_and_up = [rec for rec in caplog.records if rec.levelno >= logging.WARNING]
    assert len(warnings_and_up) == 1
    record = warnings_and_up[0]
    assert record.levelno == logging.ERROR
    assert record.message == (
        "Checksum verification FAILED [raw=3f0201234567e957, crc_given=e957, "
        "crc_calculated=e956]"
    )


@pytest.mark.parametrize(
    ("data_link_bytes", "expected"),
    [
        pytest.param(
            DataLinkData(
                destination_address=0x3F,
                application_bytes=ApplicationBytes(b"\x01"),
            ),
            DataLinkBytes(b"\x3F\x01\x05\x8A"),
            id="Kamstrup doc 6.2.1 GetType request",
        ),
        pytest.param(
            DataLinkData(
                destination_address=0x3F,
                application_bytes=ApplicationBytes(b"\x10\x01\x00\x80"),
            ),
            DataLinkBytes(b"\x3F\x10\x01\x00\x80\xD4\x08"),
            id="Kamstrup doc 6.2.4 GetRegister request",
        ),
    ],
)
def test_codec_data_link_encode(
    data_link_bytes: DataLinkData,
    expected: DataLinkBytes,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        assert DataLinkCodec().encode(data_link_bytes).hex() == expected.hex()


@pytest.mark.parametrize(
    ("data_link_data", "exc_type", "exc_message"),
    [
        pytest.param(
            DataLinkData(
                destination_address=0xFFFF,
                application_bytes=ApplicationBytes(b"\x01"),
            ),
            InvalidDestinationAddressError,
            "Invalid destination address for data link layer",
            id="invalid destination address (overflows one byte)",
        ),
        pytest.param(
            DataLinkData(
                destination_address=0x3F,
                application_bytes=ApplicationBytes(b""),
            ),
            DataLengthUnexpectedError,
            "Application data is of length 0, expected length is 1 at minimum.",
            id="no application data",
        ),
    ],
)
def test_codec_data_link_encode_error(
    data_link_data: DataLinkData,
    exc_type: type,
    exc_message: str,
) -> None:
    codec = DataLinkCodec()
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        codec.encode(data_link_data)


@pytest.mark.parametrize(
    ("data", "crc"),
    [
        pytest.param(
            DataLinkBytes(b"\x3F\x01"),
            0x058A,
            id="Kamstrup doc 6.2.1 GetType request",
        ),
        pytest.param(
            DataLinkBytes(b"\x3F\x01\x00\x04\x06\x01\x26\x99"),
            0x0000,
            id="Kamstrup doc 6.2.1 GetType response",
        ),
        pytest.param(
            DataLinkBytes(b"\x3F\x02"),
            0x35E9,
            id="Kamstrup doc 6.2.2 GetSerialNo request",
        ),
        pytest.param(
            DataLinkBytes(b"\x3F\x02\x01\x23\x45\x67\xE9\x56"),
            0x0000,
            id="Kamstrup doc 6.2.2 GetSerialNo response",
        ),
        pytest.param(
            DataLinkBytes(b"\x3f\x10\x01\x00\x80"),
            0xD408,
            id="Kamstrup doc 6.2.4 GetRegister request",
        ),
        pytest.param(
            DataLinkBytes(b"\x3F\x10\x00\x80\x16\x04\x11\x01\x2A\xF0\x24\x63\x03"),
            0x0000,
            id="Kamstrup doc 6.2.4 GetRegister response",
        ),
    ],
)
def test_codec_data_link_crc_calculator(
    data: DataLinkBytes,
    crc: int,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        assert hex(DataLinkCodec.crc_calculator.checksum(data)) == hex(crc)


@pytest.mark.parametrize(
    ("application_bytes", "expected"),
    [
        pytest.param(
            ApplicationDataBytes(b"\x02\x01\x23\x45\x67"),
            ApplicationData(
                command_id=0x02,
                data=ApplicationDataBytes(b"\x01\x23\x45\x67"),
            ),
            id="Kamstrup doc 6.2.2 GetSerialNo response",
        ),
        pytest.param(
            ApplicationDataBytes(b"\x02"),
            ApplicationData(
                command_id=0x02,
                data=ApplicationDataBytes(b""),
            ),
            id="Kamstrup doc 6.2.2 GetSerialNo request (no data for CID=10 request)",
        ),
        pytest.param(
            ApplicationDataBytes(b"\x10\x00\x80\x16\x04\x11\x01\x2A\xF0\x24"),
            ApplicationData(
                command_id=0x10,
                data=ApplicationDataBytes(b"\x00\x80\x16\x04\x11\x01\x2A\xF0\x24"),
            ),
            id="Kamstrup doc 6.2.4 GetRegister response",
        ),
    ],
)
def test_codec_application_decode(
    application_bytes: ApplicationBytes,
    expected: ApplicationData,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        assert ApplicationCodec.decode(application_bytes) == expected


@pytest.mark.parametrize(
    ("application_bytes", "exc_type", "exc_message"),
    [
        pytest.param(
            ApplicationDataBytes(b""),
            DataLengthUnexpectedError,
            "Application data message to destructure is of length 0, expected length "
            "is 1 at minimum.",
            id="empty",
        ),
    ],
)
def test_codec_application_decode_error(
    application_bytes: ApplicationBytes, exc_type: type, exc_message: str
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        ApplicationCodec.decode(application_bytes)


@pytest.mark.parametrize(
    ("application_data", "expected"),
    [
        pytest.param(
            ApplicationData(
                command_id=0x01,
                data=ApplicationDataBytes(b""),
            ),
            ApplicationDataBytes(b"\x01"),
            id="Kamstrup doc 6.2.1 GetType request CID=1, no data",
        ),
        pytest.param(
            ApplicationData(
                command_id=0x10,
                data=ApplicationDataBytes(b"\x01\x00\x80"),
            ),
            ApplicationDataBytes(b"\x10\x01\x00\x80"),
            id="Kamstrup doc 6.2.4 GetRegister request CID=10, with data",
        ),
    ],
)
def test_codec_application_encode(
    application_data: ApplicationData,
    expected: ApplicationBytes,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        assert ApplicationCodec.encode(application_data).hex() == expected.hex()


@pytest.mark.parametrize(
    ("application_data", "exc_type", "exc_message"),
    [
        pytest.param(
            ApplicationData(
                command_id=0xFFFF,
                data=ApplicationDataBytes(b""),
            ),
            OutOfRangeError,
            "Command ID is out of range [0,255]: 65535.",
            id="invalid command ID (overflows 1 byte)",
        ),
    ],
)
def test_codec_application_encode_error(
    application_data: ApplicationData,
    exc_type: type,
    exc_message: str,
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        ApplicationCodec.encode(application_data)


@pytest.mark.parametrize(
    ("encoded", "expected_int_or_float", "expected_decimal"),
    [
        pytest.param(
            b"\x04\xC2\x00\x00\x30\x39",
            -123.45,
            decimal.Decimal("-123.45"),
            id="Kamstrup doc 4.2 example 1 [si=1, se=1, exp=2]",
        ),
        pytest.param(
            b"\x04\x03\x05\x39\x7F\xB1",
            87_654_321_000,
            decimal.Decimal("87654321000"),
            id="Kamstrup doc 4.2 example 2 [si=0, se=0, exp=3]",
        ),
        pytest.param(
            b"\x01\x03\xFF",
            255_000,
            decimal.Decimal("255000"),
            id="Kamstrup doc 4.2 example 3 [si=0, se=0, exp=3]",
        ),
        pytest.param(
            b"\x04\x11\x01\x2A\xF0\x24",
            19591204 * (10**17),
            decimal.Decimal("1959120400000000000000000"),
            id="Kamstrup doc 6.2.4 GetRegister response [si=0, se=0, exp=17]",
        ),
        pytest.param(
            b"\x04\x43\x00\x00\x00\xfb",
            0.251,
            decimal.Decimal("0.251"),
            id="some real (regular) value from Multical 403 [si=0, se=1, exp=3]",
        ),
        pytest.param(
            b"\x02\x42\x18\xC8",
            63.440000000000005,
            decimal.Decimal("63.44"),
            id="demonstrating floating point error [si=0, se=1, exp=2]",
        ),
    ],
)
def test_codec_float_symmetry(
    encoded: bytes,
    # Not annotated as 'float | int', as 'int' is a subtype of 'float'. 🤷
    # See Ruff rule description PYI041 & https://peps.python.org/pep-3141/.
    expected_int_or_float: float,
    expected_decimal: decimal.Decimal,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        value_decimal = FloatCodec.decode(encoded)
        value_int_or_float = FloatCodec.decode_int_or_float(encoded)
        assert value_decimal == expected_decimal
        assert value_int_or_float == expected_int_or_float
        assert isinstance(value_int_or_float, type(expected_int_or_float))
        assert (
            FloatCodec.encode(
                to_encode=expected_decimal,
                # Encode with same length as given.
                significand_num_bytes=len(encoded) - 2,
            ).hex()
            == encoded.hex()
        )


@pytest.mark.parametrize(
    ("encoded_orig", "expected_shortest"),
    [
        pytest.param(
            b"\x04\xC2\x00\x00\x00\x39",
            b"\x01\xC2\x39",
            id="length 4 to 1",
        ),
        pytest.param(
            b"\x04\xC2\x00\x00\x30\x39",
            b"\x02\xC2\x30\x39",
            id="length 4 to 2",
        ),
        pytest.param(
            b"\x04\x11\x01\x2A\xF0\x24",
            b"\x04\x11\x01\x2A\xF0\x24",
            id="length 4 (unchanged)",
        ),
        pytest.param(
            b"\x05\x11\x01\x01\x2A\xF0\x24",
            b"\x04\x13\x02\x92\x59\x71",
            id="length 5 to 4",
        ),
    ],
)
def test_codec_float_shorter_form(
    encoded_orig: bytes,
    expected_shortest: bytes,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        decoded_decimal_orig = FloatCodec.decode(encoded_orig)
        shortest = FloatCodec.encode(
            to_encode=decoded_decimal_orig, significand_num_bytes=None
        )
        assert shortest.hex() == expected_shortest.hex()
        assert FloatCodec.decode(shortest) == decoded_decimal_orig


@pytest.mark.parametrize(
    ("float_encoded", "exc_type", "exc_message"),
    [
        pytest.param(
            b"\x05\xC2\x00\x00\x30\x39",
            DataLengthUnexpectedError,
            "Floating point data is of length 6, expected length is 7.",
            id="length byte 5 instead of 4",
        ),
        pytest.param(
            b"\x03\xC2\x00\x00\x30\x39",
            DataLengthUnexpectedError,
            "Floating point data is of length 6, expected length is 5.",
            id="length byte 3 instead of 4",
        ),
        pytest.param(
            b"\x00\xC2",
            OutOfRangeError,
            "Integer length byte value for floating point data decoding is under "
            "minimum of 1: 0.",
            id="integer length 0 is invalid",
        ),
        pytest.param(
            b"",
            DataLengthUnexpectedError,
            "Data for floating point decoding is of zero length.",
            id="empty",
        ),
    ],
)
def test_codec_float_decode_error(
    float_encoded: bytes, exc_type: type, exc_message: str
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        FloatCodec.decode(float_encoded)
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        FloatCodec.decode_int_or_float(float_encoded)


@pytest.mark.parametrize(
    ("to_encode", "significand_num_bytes", "exc_type", "exc_message"),
    [
        pytest.param(
            decimal.Decimal("12345678901234567890"),
            4,
            OutOfRangeError,
            (
                "Significand bytes length of decimal to encode as mantissa is out of "
                "range [4,4]: 8."
            ),
            id="mantissa too big for size=4",
        ),
        # TODO: We should do better here by encoding more in the mantissa rather than
        # going for the optimal encoded size.
        pytest.param(
            decimal.Decimal("1.1E+65"),
            4,
            OutOfRangeError,
            "Exponent (64) to encode is over maximum of 63: 64.",
            id="exponent 64 does not fit in 6 bits",
        ),
        pytest.param(
            decimal.Decimal("NaN"),
            4,
            UnsupportedDecimalExponentError,
            "Unsupported exponent n where an integer is expected.",
            id="NaN can't be encoded",
        ),
    ],
)
def test_codec_float_encode_error(
    to_encode: decimal.Decimal,
    significand_num_bytes: int | None,
    exc_type: type,
    exc_message: str,
) -> None:
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        FloatCodec.encode(
            to_encode=to_encode, significand_num_bytes=significand_num_bytes
        )
