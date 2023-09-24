# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

"""
Low-level codec classes for the Kamstrup KMP protocol.

This contains decoders/encoders for the Physical, Data Link and Application layer
(generics).

Logic for specific messages (requests and responses) are not part of this module, but
generic codecs such as floating point data format encoding/decoding used in
requests/responses *are*.
"""

from __future__ import annotations

import decimal
import enum
import logging
import math
from typing import Any, Final, Literal, NewType, cast

import attrs
import crc  # pyright: ignore [reportMissingTypeStubs]

from . import constants

logger = logging.getLogger(__name__)


PhysicalBytes = NewType("PhysicalBytes", bytes)
DataLinkBytes = NewType("DataLinkBytes", bytes)
ApplicationBytes = NewType("ApplicationBytes", bytes)
ApplicationDataBytes = NewType("ApplicationDataBytes", bytes)


class AckReceivedException(Exception):  # noqa: N818
    """Not an error; it was just an ACK and no data link bytes to return."""


class BaseCodecError(Exception):
    """Base error for anything that originates from logic here."""


@attrs.define(kw_only=True)
class OutOfRangeError(BaseCodecError):
    """
    A value was found outside of a valid range.

    Supports ranges with both lower and upper bounds, only upper and only lower. Range
    is inclusive.
    """

    what: str
    valid_range: tuple[int, int] | tuple[int, None] | tuple[None, int]  # inclusive
    actual: int

    def __str__(self) -> str:  # noqa: D105
        match self.valid_range:
            case (int(lower), int(upper)):
                return f"{self.what} is out of range [{lower},{upper}]: {self.actual}."
            case (None, int(upper)):
                return f"{self.what} is over maximum of {upper}: {self.actual}."
            case (int(lower), None):
                return f"{self.what} is under minimum of {lower}: {self.actual}."
            # Instead of a 'type: ignore[return]', help mypy with an unreachable default
            # case. Looks like https://github.com/python/mypy/issues/12364.
            # Pyright is right here, so suppress that one.
            case _:  # pyright: ignore[reportUnnecessaryComparison]  # pragma: nocover
                raise RuntimeError  # pragma: nocover


@attrs.define(kw_only=True)
class DataLengthUnexpectedError(BaseCodecError):  # noqa: D101
    what: str
    actual: int
    length_expected: int | None = None
    expected_is_minimum: bool = False

    def __str__(self) -> str:  # noqa: D105
        if self.length_expected is not None:
            return (
                f"{self.what} is of length {self.actual}, expected length is "
                f"{self.length_expected}"
                f"{' at minimum' if self.expected_is_minimum else ''}."
            )
        return (
            f"{self.what} is of {'zero' if self.actual == 0 else 'unexpected'} length."
        )


@attrs.define(kw_only=True)
class BoundaryByteInvalidError(BaseCodecError):
    """First or last byte is not a start or stop byte respectively."""

    what: Literal["start", "stop"]
    expected_byte: int
    actual_byte: int

    def __str__(self) -> str:  # noqa: D105
        return (
            f"Frame expected {self.what} byte is {self.expected_byte} (hex: "
            f"{self.expected_byte:02X}), but got {self.actual_byte} "
            f"(hex: {self.actual_byte:02X})"
        )


class InvalidDestinationAddressError(BaseCodecError):
    """Destination address for the data link layer is not within valid range."""

    def __str__(self) -> str:  # noqa: D105
        return "Invalid destination address for data link layer"


@attrs.frozen(kw_only=True)
class UnsupportedDecimalExponentError(BaseCodecError):
    """The Decimal value cannot be encoded to a base-10 float (non-integer exponent)."""

    actual_exponent: Any

    def __str__(self) -> str:  # noqa: D105
        return (
            f"Unsupported exponent {self.actual_exponent} where an integer is expected."
        )


class CrcChecksumInvalidError(BaseCodecError):
    """CRC checksum validation of the data link byte sequence did not pass."""


@attrs.frozen(kw_only=True)
class ApplicationData:
    """Data class for the data in the application layer of the Kamstrup KMP protocol."""

    command_id: int
    data: ApplicationDataBytes


@attrs.frozen(kw_only=True)
class DataLinkData:
    """Data class for the data in the data link layer of the Kamstrup KMP protocol."""

    destination_address: int
    application_bytes: ApplicationBytes
    crc_value: int | None = None


class PhysicalDirection(enum.Enum):
    """Specifies the direction of communication for the Kamstrup KMP protocol."""

    TO_METER = enum.auto()
    FROM_METER = enum.auto()


@attrs.define(kw_only=True, slots=False, auto_attribs=False)
class PhysicalCodec:
    """
    Codec for the physical layer of the Kamstrup KMP protocol.

    This codec is responsible for encoding/decoding a frame to/from the data link layer
    message for writing/reading to/from the IR head. What it does is:

    - Adding/removing start/stop bytes.
    - Stuffing/destuffing some special byte values.

    Note that the codec is slightly different for sending or receiving messages to/from
    the meter.

    See section 3.1 of the KMP protocol description document.
    """

    direction: PhysicalDirection = attrs.field()
    _start_byte: int = attrs.field(init=False)  # depends on direction

    BYTE_STUFFING_MAP: Final[dict[bytes, bytes]] = {
        the_byte.to_bytes(1, "big"): (
            constants.ByteCode.STUFFING.value.to_bytes(1, "big")
            + (the_byte ^ 0xFF).to_bytes(1, "big")
        )
        for the_byte in (
            # Order matters for having BYTE_STUFFING as the first; itself is used in the
            # escaped sequence.
            constants.ByteCode.STUFFING.value,
            constants.ByteCode.ACK.value,
            constants.ByteCode.START_FROM_METER.value,
            constants.ByteCode.START_TO_METER.value,
            constants.ByteCode.STOP.value,
        )
    }

    def __attrs_post_init__(self) -> None:
        """Select start byte value according to configuration (direction)."""
        self._start_byte = self._direction_to_start_byte(self.direction)

    @classmethod
    def _direction_to_start_byte(cls, direction: PhysicalDirection) -> int:
        # In separate function for having exhaustive check during type checking.
        match direction:
            case PhysicalDirection.FROM_METER:
                return constants.ByteCode.START_FROM_METER.value
            case PhysicalDirection.TO_METER:
                return constants.ByteCode.START_TO_METER.value

    def decode(self, frame: PhysicalBytes) -> DataLinkBytes:
        """
        Decode a byte sequence of the physical layer into 'DataLinkBytes'.

        The `frame` must start with a start byte and ends with an end byte, unless it's
        an ACK frame.
        """
        if not frame:
            raise DataLengthUnexpectedError(
                what="Frame", actual=0, length_expected=None
            )

        if frame == constants.ACK_BYTES:
            # The ACK is an APL level acknowledge, but send as a single byte without
            # start, CRC or stop bytes. See also example Kamstrup doc 6.2.3 (SetClock).
            raise AckReceivedException

        if not frame.startswith(self._start_byte.to_bytes(1, "big")):
            raise BoundaryByteInvalidError(
                what="start", actual_byte=frame[0], expected_byte=self._start_byte
            )
        if not frame.endswith(constants.ByteCode.STOP.value.to_bytes(1, "big")):
            raise BoundaryByteInvalidError(
                what="stop",
                actual_byte=frame[-1],
                expected_byte=constants.ByteCode.STOP.value,
            )

        data_bytes = frame[1:-1]
        for unescaped_byte, escaped_bytes in self.BYTE_STUFFING_MAP.items():
            data_bytes = data_bytes.replace(escaped_bytes, unescaped_byte)

        return cast(DataLinkBytes, data_bytes)

    def encode(self, data_bytes: DataLinkBytes) -> PhysicalBytes:
        """
        Encode a byte sequence of the data link layer into 'PhysicalBytes'.

        This 'stuffs' the special byte values and adds start/stop bytes.

        For encoding an ACK message, see encode_ack().
        """
        if not len(data_bytes):
            raise DataLengthUnexpectedError(
                what="Data link bytes", actual=0, length_expected=None
            )

        raw = cast(bytes, data_bytes)
        for unescaped_byte, escaped_bytes in self.BYTE_STUFFING_MAP.items():
            raw = raw.replace(unescaped_byte, escaped_bytes)

        frame = (
            self._start_byte.to_bytes(1, "big")
            + raw
            + constants.ByteCode.STOP.value.to_bytes(1, "big")
        )
        return cast(PhysicalBytes, frame)

    @classmethod
    def encode_ack(cls) -> PhysicalBytes:
        """
        Encode an ACK message.

        This type of message does not need andy stuffing or start/stop bytes.
        """
        return cast(PhysicalBytes, constants.ACK_BYTES)


def _create_kamstrup_crc16_ccitt_calculator(*, initial: int = 0x0000) -> crc.Calculator:
    """
    CRC-16 CCITT checksum calculator with non-standard initial value.

    Included in the data link layer is a CRC with reference to the CCITT-standard using
    the polynomial 1021h. Only deviation from the standard is the initial value, which
    is 0000h instead of FFFFh.
    """
    configuration = crc.Configuration(
        width=16,
        polynomial=0x1021,
        init_value=initial,
        final_xor_value=0x0000,
        reverse_input=False,
        reverse_output=False,
    )
    return crc.Calculator(configuration, optimized=True)


@attrs.define(kw_only=True, slots=True, auto_attribs=False)
class DataLinkCodec:
    """
    Codec for the data link layer of the Kamstrup KMP protocol.

    This codec is responsible for encoding/decoding to/from the application layer
    messages. What it does is:

    - Destructuring the byte sequence into a destination address, application layer byte
      sequence and a CRC checksum.
    - CRC checksum calculation/verification.

    See section 3.2 of the KMP protocol description document.
    """

    DATA_LINK_BYTES_LENGTH_MIN: Final[int] = 4
    APPLICATION_BYTES_LENGTH_MIN: Final[int] = 1

    crc_calculator: Final[crc.Calculator] = _create_kamstrup_crc16_ccitt_calculator()

    def decode(self, raw: DataLinkBytes) -> DataLinkData:
        """
        Decode a byte sequence of the data link layer into 'DataLinkData'.

        This destructures it into the destination address, the application data and the
        CRC checksum. Also the latter will be verified.
        """
        if not len(raw) >= self.DATA_LINK_BYTES_LENGTH_MIN:
            raise DataLengthUnexpectedError(
                what="Data link layer message to destructure",
                actual=len(raw),
                length_expected=self.DATA_LINK_BYTES_LENGTH_MIN,
                expected_is_minimum=True,
            )

        destination_address, application_bytes, crc_bytes = raw[0], raw[1:-2], raw[-2:]

        crc_verifies = self.crc_calculator.verify(raw, expected=0)
        logger.log(
            logging.DEBUG if crc_verifies else logging.ERROR,
            "Checksum verification %s [raw=%s, crc_given=%s, crc_calculated=%s]",
            "OK" if crc_verifies else "FAILED",
            raw.hex(),
            crc_bytes.hex(),
            "OK"
            if crc_verifies
            else hex(self.crc_calculator.checksum(raw[:-2])).removeprefix("0x"),
        )
        if not crc_verifies:
            raise CrcChecksumInvalidError

        return DataLinkData(
            destination_address=destination_address,
            application_bytes=cast(ApplicationBytes, application_bytes),
            crc_value=int.from_bytes(crc_bytes, "big"),
        )

    def encode(self, data: DataLinkData) -> DataLinkBytes:
        """
        Encode a byte sequence of the application layer into 'DataLinkBytes'.

        The structure includes the destination address and a CRC checksum (calculated
        here).
        """
        try:
            destination_address_raw = data.destination_address.to_bytes(1, "big")
        except OverflowError as exc:
            raise InvalidDestinationAddressError from exc

        if len(data.application_bytes) < self.APPLICATION_BYTES_LENGTH_MIN:
            raise DataLengthUnexpectedError(
                what="Application data",
                actual=len(data.application_bytes),
                length_expected=self.APPLICATION_BYTES_LENGTH_MIN,
                expected_is_minimum=True,
            )

        raw_before_crc = destination_address_raw + data.application_bytes

        crc = self.crc_calculator.checksum(raw_before_crc)
        crc_bytes = (crc).to_bytes(2, "big")

        return cast(DataLinkBytes, raw_before_crc + crc_bytes)


@attrs.define(kw_only=True, slots=True, auto_attribs=False)
class ApplicationCodec:
    """
    Codec for the application layer of the Kamstrup KMP protocol.

    This codec is responsible for encoding/decoding to/from the command data byte
    sequences. What it does is destructuring the byte sequence into a Command ID (CID)
    and the command data.

    Note that this covers both requests and responses and command data may be emtpy.

    See section 3.3 of the KMP protocol description document.
    """

    APPLICATION_BYTES_LENGTH_MIN: Final[int] = 1

    @classmethod
    def decode(cls, data: ApplicationBytes) -> ApplicationData:
        """Decode a byte sequence of the application layer into 'ApplicationData'."""
        if not len(data) >= cls.APPLICATION_BYTES_LENGTH_MIN:
            raise DataLengthUnexpectedError(
                what="Application data message to destructure",
                length_expected=cls.APPLICATION_BYTES_LENGTH_MIN,
                expected_is_minimum=True,
                actual=len(data),
            )
        return ApplicationData(
            command_id=data[0],
            data=cast(ApplicationDataBytes, data[1:]),
        )

    @classmethod
    def encode(cls, to_encode: ApplicationData) -> ApplicationBytes:
        """Encode to a byte sequence of the application layer 'ApplicationBytes'."""
        try:
            command_id_raw = to_encode.command_id.to_bytes(1, "big")
        except OverflowError as exc:
            raise OutOfRangeError(
                what="Command ID",
                valid_range=(0, 255),
                actual=to_encode.command_id,
            ) from exc

        return cast(ApplicationBytes, command_id_raw + to_encode.data)


@attrs.define(kw_only=True, slots=True, auto_attribs=False)
class FloatCodec:
    """
    Codec for the variable length base-10 floating point format in the KMP protocol.

    The length of the mantissa is encoded and is commonly 32 bits (4 bytes).
    A visual representation of the format using an example:

    ```
    data: 0x024300FB

        0x02     0x43     0x00     0xFB (hex)
    00000010 01000011 00000000 11111011 (bin)

    00000010 ________ ________ ________ <- length of significand
    ________ 0_______ ________ ________ <- sign bit for significand 'SI' (1=negative)
    ________ _1______ ________ ________ <- sign bit for exponent 'SE'
    ________ __000011 ________ ________ <- 6 exponent bits
    ________ ________ 00000000 11111011 <- significand (int) 'mantissa'
    ```

    In the above example:
    - 0x02 decodes to a length of 2 bytes = 16 bits to read for the mantissa.
    - SI=0, so a positive value.
    - SE=1, thus a negative exponent.
    - exponent=0x03 = 3 (decimal)
    - mantissa=0x00FB = 251 (decimal)

    Calculation with the above example data:

    ```
        -1|1 * (mantissa * 10 ^ ( -1|1   * exponent )

          1  * (  251    * 10 ^ (  -1    *    3     ) = 0.251
    ```

    In short, The mantissa holds the significands of the data, the others are just for
    scale.

    See also section 4.2 of the KMP protocol description document.
    """

    @classmethod
    def _decode_parts(cls, data: bytes) -> tuple[bool, bool, int, int]:
        if not data:
            raise DataLengthUnexpectedError(
                what="Data for floating point decoding", actual=len(data)
            )

        integer_length = data[0]
        logger.debug(
            "Decoding parts of floating point data. [data=%r, integer_length=%d]",
            data.hex().upper(),
            integer_length,
        )

        if not integer_length:
            raise OutOfRangeError(
                what="Integer length byte value for floating point data decoding",
                valid_range=(1, None),
                actual=0,
            )

        length_expected = integer_length + 2
        if len(data) != length_expected:
            raise DataLengthUnexpectedError(
                what="Floating point data",
                actual=len(data),
                length_expected=length_expected,
            )

        sign_exp_byte = data[1]
        mantissa = int.from_bytes(data[2 : integer_length + 2], "big")
        negative, exponent_negative, exponent = (
            bool((sign_exp_byte & 0b10000000) >> 7),
            bool((sign_exp_byte & 0b01000000) >> 6),
            sign_exp_byte & 0b00111111,
        )
        return negative, exponent_negative, exponent, mantissa

    @classmethod
    def decode(cls, data: bytes) -> decimal.Decimal:
        """Decode a byte sequence of a floating point format to a decimal.Decimal."""
        negative, exponent_negative, _exponent, mantissa = cls._decode_parts(data)
        mantissa_digits = tuple(int(digit) for digit in str(mantissa))
        exponent = -_exponent if exponent_negative else _exponent
        # Leverage the convenient three-item tuple constructor here.
        ret = decimal.Decimal((negative, mantissa_digits, exponent))
        logger.debug(
            "Decoded floating point data: %r [data=%r, man=%d, si=%s, se=%s, exp=%d]",
            ret,
            data.hex().upper(),
            mantissa,
            negative,
            exponent_negative,
            _exponent,
        )
        return ret

    @classmethod
    def decode_int_or_float(cls, data: bytes) -> int | float:
        """
        Decode a KMP protocol byte sequence of a floating point as int or float.

        Returns an int if it can be encoded as a int ("nothing after the comma") to
        avoid losing significance.

        This implements an alternative way to decoding the base-10 floating point. It is
        included for reference/testing. It may be slow or one may be unfamiliar with
        Python's decimal.Decimal types. Note that you may lose significance in this
        conversion to float, or some infamous floating point error like
        '63.440000000000005' instead of '63.44'.

        Its use is discouraged and if one needs a float then convert the returned
        decimal.Decimal from the regular `decode()` method.
        """
        negative, exponent_negative, _exponent, mantissa = cls._decode_parts(data)
        ret: int | float
        if not exponent_negative:
            # Final value remains integer; avoids unnecessary float imprecision for
            # cases without shifting the decimal point left.
            ret = mantissa * int(math.pow(10, _exponent))
        else:
            ret = mantissa * math.pow(10, -_exponent)
        logger.debug(
            "Decoded floating point data: %f [data=%r, man=%d, si=%s, se=%s, exp=%d]",
            ret,
            data.hex().upper(),
            mantissa,
            negative,
            exponent_negative,
            _exponent,
        )
        return -ret if negative else ret

    @classmethod
    def encode(
        cls, *, to_encode: decimal.Decimal, significand_num_bytes: int | None = 4
    ) -> bytes:
        """Encode a decimal.Decimal value to a byte sequence in the KMP protocol."""
        decimal_tuple = to_encode.normalize().as_tuple()
        negative, digits, exponent = (
            bool(decimal_tuple.sign),
            decimal_tuple.digits,
            decimal_tuple.exponent,
        )

        if not isinstance(exponent, int):
            raise UnsupportedDecimalExponentError(actual_exponent=exponent)

        mantissa = int("".join(str(digit) for digit in digits))
        mantissa_bytes_length_needed = math.ceil(mantissa.bit_length() / 8)
        if significand_num_bytes is not None:
            if mantissa_bytes_length_needed > significand_num_bytes:
                raise OutOfRangeError(
                    what="Significand bytes length of decimal to encode as mantissa",
                    valid_range=(significand_num_bytes, significand_num_bytes),
                    actual=mantissa_bytes_length_needed,
                )
            mantissa_bytes_length = significand_num_bytes
        else:
            mantissa_bytes_length = mantissa_bytes_length_needed
        exponent_negative = exponent < 0
        _exponent: int = abs(exponent)
        max_value_six_bits = 0b00111111
        if _exponent > max_value_six_bits:
            raise OutOfRangeError(
                what=f"Exponent ({_exponent}) to encode",
                valid_range=(None, max_value_six_bits),
                actual=_exponent,
            )
        mantissa_lengh_byte = mantissa_bytes_length.to_bytes(1, "big")
        sign_bit = int(negative) << 7
        exponent_sign_bit = int(exponent_negative) << 6
        exponent_bits = _exponent & 0b00111111
        sign_exp_byte = (sign_bit | exponent_sign_bit | exponent_bits).to_bytes(
            1, "big"
        )
        mantissa_bytes = mantissa.to_bytes(mantissa_bytes_length, "big")
        return mantissa_lengh_byte + sign_exp_byte + mantissa_bytes
