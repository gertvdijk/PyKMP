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
    ("direction", "frame", "data_link"),
    [
        pytest.param(
            PhysicalDirection.TO_METER,
            "80 04 1BF2 00 1BF9 0D",
            "   04 0D   00 06     ",
            id="Kamstrup doc 3.1 Physical layer example, plus start/stop byte",
        ),
        pytest.param(
            PhysicalDirection.TO_METER,
            "80 3F 01 058A 0D",
            "   3F 01 058A   ",
            id="Kamstrup doc 6.2.1 GetType request (no stuffing needed)",
        ),
        pytest.param(
            PhysicalDirection.FROM_METER,
            "40 3F 02 01234567 E956 0D",
            "   3F 02 01234567 E956   ",
            id="Kamstrup doc 6.2.2 GetSerialNo response (no destuffing needed)",
        ),
        pytest.param(
            PhysicalDirection.TO_METER,
            "80 3F 10 01 00 1B7F D408 0D",
            "   3F 10 01 00 80   D408   ",
            id="Kamstrup doc 6.2.4 GetRegister request (stuffing needed)",
        ),
        pytest.param(
            PhysicalDirection.FROM_METER,
            "40 3F 10 00 1B7F 16 04 11 012AF024 6303 0D",
            "   3F 10 00   80 16 04 11 012AF024 6303   ",
            id="Kamstrup doc 6.2.4 GetRegister response (destuffing needed)",
        ),
        pytest.param(
            PhysicalDirection.TO_METER,
            "80 1BE4 0D",
            "   1B     ",
            id="stuffing stuff byte",
        ),
    ],
)
def test_codec_physical_decode_encode(
    direction: PhysicalDirection,
    frame: str,
    data_link: str,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        decoded = PhysicalCodec(direction=direction).decode(
            PhysicalBytes(bytes.fromhex(frame))
        )
        encoded = PhysicalCodec(direction=direction).encode(
            DataLinkBytes(bytes.fromhex(data_link))
        )
    assert decoded.hex() == bytes.fromhex(data_link).hex()
    assert encoded.hex() == bytes.fromhex(frame).hex()


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
            "80 56 0D",
            BoundaryByteInvalidError,
            "Frame expected start byte is 64 (hex: 40), but got 128 (hex: 80)",
            id="wrong start byte (FROM_METER)",
        ),
        pytest.param(
            PhysicalDirection.TO_METER,
            "40 56 0D",
            BoundaryByteInvalidError,
            "Frame expected start byte is 128 (hex: 80), but got 64 (hex: 40)",
            id="wrong start byte (TO_METER)",
        ),
        pytest.param(
            PhysicalDirection.FROM_METER,
            "40 56",
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
    frame: str,
    exc_type: type,
    exc_message: str,
) -> None:
    codec = PhysicalCodec(direction=direction)
    with pytest.raises(exc_type, match=util.full_match_re(exc_message)):
        codec.decode(PhysicalBytes(bytes.fromhex(frame)))


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
    ("data_link_bytes", "expected_app_bytes", "expected_crc"),
    [
        pytest.param(
            "3F 02 01234567 E956",
            "   02 01234567     ",
            0xE956,
            id="Kamstrup doc 6.2.2 GetSerialNo response",
        ),
        pytest.param(
            "3F 10 0080 16 04 11 012AF024 6303",
            "   10 0080 16 04 11 012AF024     ",
            0x6303,
            id="Kamstrup doc 6.2.4 GetRegister response",
        ),
    ],
)
def test_codec_data_link_decode(
    data_link_bytes: str,
    expected_app_bytes: str,
    expected_crc: int,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    expected = DataLinkData(
        destination_address=0x3F,
        application_bytes=ApplicationBytes(bytes.fromhex(expected_app_bytes)),
        crc_value=expected_crc,
    )
    with ensure_no_warnings_logged():
        assert (
            DataLinkCodec().decode(DataLinkBytes(bytes.fromhex(data_link_bytes)))
            == expected
        )


@pytest.mark.parametrize(
    ("data_link_bytes", "exc_type", "exc_message"),
    [
        pytest.param(
            DataLinkBytes(bytes.fromhex("56")),
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
    # Kamstrup doc 6.2.2 GetSerialNo response with broken checksum (correct: 'E956')
    broken_data_link_bytes = DataLinkBytes(bytes.fromhex("3F 02 01234567 E957"))

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
    ("data_link_in", "data_link_encoded"),
    [
        pytest.param(
            "   01",
            "3F 01 058A",
            id="Kamstrup doc 6.2.1 GetType request",
        ),
        pytest.param(
            "   10 01 0080",
            "3F 10 01 0080 D408",
            id="Kamstrup doc 6.2.4 GetRegister request",
        ),
    ],
)
def test_codec_data_link_encode(
    data_link_in: str,
    data_link_encoded: str,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    data_link_data = DataLinkData(
        destination_address=0x3F,
        application_bytes=ApplicationBytes(bytes.fromhex(data_link_in)),
    )
    expected_bytes = DataLinkBytes(bytes.fromhex(data_link_encoded))
    with ensure_no_warnings_logged():
        assert DataLinkCodec().encode(data_link_data).hex() == expected_bytes.hex()


@pytest.mark.parametrize(
    ("data_link_data", "exc_type", "exc_message"),
    [
        pytest.param(
            DataLinkData(
                destination_address=0xFFFF,
                application_bytes=ApplicationBytes(bytes.fromhex("01")),
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
            DataLinkBytes(bytes.fromhex("3F 01")),
            0x058A,
            id="Kamstrup doc 6.2.1 GetType request",
        ),
        pytest.param(
            DataLinkBytes(bytes.fromhex("3F 01 0004 0601 2699")),
            0x0000,
            id="Kamstrup doc 6.2.1 GetType response",
        ),
        pytest.param(
            DataLinkBytes(bytes.fromhex("3F 02")),
            0x35E9,
            id="Kamstrup doc 6.2.2 GetSerialNo request",
        ),
        pytest.param(
            DataLinkBytes(bytes.fromhex("3F 02 01234567 E956")),
            0x0000,
            id="Kamstrup doc 6.2.2 GetSerialNo response",
        ),
        pytest.param(
            DataLinkBytes(bytes.fromhex("3F 10 01 0080")),
            0xD408,
            id="Kamstrup doc 6.2.4 GetRegister request",
        ),
        pytest.param(
            DataLinkBytes(bytes.fromhex("3F 10 0080 16 04 11 012AF024 6303")),
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
    ("application_bytes", "expected_cid", "expected_app_bytes"),
    [
        pytest.param(
            bytes.fromhex("02 01234567"),
            0x02,
            bytes.fromhex("   01234567"),
            id="Kamstrup doc 6.2.2 GetSerialNo response",
        ),
        pytest.param(
            bytes.fromhex("02"),
            0x02,
            bytes.fromhex(""),
            id="Kamstrup doc 6.2.2 GetSerialNo request (no data for CID=10 request)",
        ),
        pytest.param(
            bytes.fromhex("10 0080 16 04 11 012AF024"),
            0x10,
            bytes.fromhex("   0080 16 04 11 012AF024"),
            id="Kamstrup doc 6.2.4 GetRegister response",
        ),
    ],
)
def test_codec_application_decode(
    application_bytes: bytes,
    expected_cid: int,
    expected_app_bytes: bytes,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    with ensure_no_warnings_logged():
        expected = ApplicationData(
            command_id=expected_cid, data=ApplicationDataBytes(expected_app_bytes)
        )
        assert ApplicationCodec.decode(ApplicationBytes(application_bytes)) == expected


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
    ("cid", "app_bytes", "expected"),
    [
        pytest.param(
            0x01,
            bytes.fromhex("  "),
            bytes.fromhex("01"),
            id="Kamstrup doc 6.2.1 GetType request CID=1, no data",
        ),
        pytest.param(
            0x10,
            bytes.fromhex("   01 00 80"),
            bytes.fromhex("10 01 00 80"),
            id="Kamstrup doc 6.2.4 GetRegister request CID=10, with data",
        ),
    ],
)
def test_codec_application_encode(
    cid: int,
    app_bytes: bytes,
    expected: bytes,
    ensure_no_warnings_logged: util.SimpleContextTest,
) -> None:
    application_data = ApplicationData(
        command_id=cid,
        data=ApplicationDataBytes(app_bytes),
    )
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
            bytes.fromhex("04 C2 00003039"),
            -123.45,
            decimal.Decimal("-123.45"),
            id="Kamstrup doc 4.2 example 1 [si=1, se=1, exp=2]",
        ),
        pytest.param(
            bytes.fromhex("04 03 05397FB1"),
            87_654_321_000,
            decimal.Decimal(87654321000),
            id="Kamstrup doc 4.2 example 2 [si=0, se=0, exp=3]",
        ),
        pytest.param(
            bytes.fromhex("01 03 FF"),
            255_000,
            decimal.Decimal(255000),
            id="Kamstrup doc 4.2 example 3 [si=0, se=0, exp=3]",
        ),
        pytest.param(
            bytes.fromhex("04 11 012AF024"),
            19591204 * (10**17),
            decimal.Decimal(1959120400000000000000000),
            id="Kamstrup doc 6.2.4 GetRegister response [si=0, se=0, exp=17]",
        ),
        pytest.param(
            bytes.fromhex("04 43 000000FB"),
            0.251,
            decimal.Decimal("0.251"),
            id="some real (regular) value from Multical 403 [si=0, se=1, exp=3]",
        ),
        pytest.param(
            bytes.fromhex("02 42 18C8"),
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
            bytes.fromhex("04 C2 00000039"),
            bytes.fromhex("01 C2       39"),
            id="length 4 to 1",
        ),
        pytest.param(
            bytes.fromhex("04 C2 00003039"),
            bytes.fromhex("02 C2     3039"),
            id="length 4 to 2",
        ),
        pytest.param(
            bytes.fromhex("04 11 012AF024"),
            bytes.fromhex("04 11 012AF024"),
            id="length 4 (unchanged)",
        ),
        pytest.param(
            bytes.fromhex("05 11 01012AF024"),
            bytes.fromhex("04 13   02925971"),
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
            bytes.fromhex("05 C2 00003039"),
            DataLengthUnexpectedError,
            "Floating point data is of length 6, expected length is 7.",
            id="length byte 5 instead of 4",
        ),
        pytest.param(
            bytes.fromhex("03 C2 00003039"),
            DataLengthUnexpectedError,
            "Floating point data is of length 6, expected length is 5.",
            id="length byte 3 instead of 4",
        ),
        pytest.param(
            bytes.fromhex("00 C2"),
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
            decimal.Decimal(12345678901234567890),
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
