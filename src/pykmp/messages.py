# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

"""KMP protocol application level decoding/encoding (requests and responses)."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, ClassVar, NewType, Protocol, TypeVar, cast

import attrs

from . import codec, constants

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping  # pragma: no cover

    from typing_extensions import Self  # pragma: no cover


Req_t_co = TypeVar("Req_t_co", bound="BaseRequest[Any]", covariant=True)
Res_t_co = TypeVar("Res_t_co", bound="BaseResponse[Any]", covariant=True)


logger = logging.getLogger(__name__)

ZERO_TO_255_RE = re.compile(
    r"""
    (
        1?[0-9]{1,2}  # 0-199
        |
        2[0-4][0-9]   # 200-249
        |
        25[0-5]       # 250-255
    )
    """,
    re.VERBOSE,
)


@attrs.define(kw_only=True)
class MessageCidMismatchError(codec.BaseCodecError):
    """Command ID in data does not match the ID defined for the class to decode to."""

    message_class_name: str
    cid_expected: int
    actual: int

    def __str__(self) -> str:  # noqa: D105
        return (
            f"Expected Command ID {self.cid_expected} for {self.message_class_name}, "
            f"got {self.actual}."
        )


@attrs.define(kw_only=True)
class DataWithNoDataError(codec.BaseCodecError):
    """Unexpected data for command that does not accept any (aside the command ID)."""

    message_class: type[HasCommandIdAndName]

    def __str__(self) -> str:  # noqa: D105
        return f"{self.message_class.__name__} does not take any data."


@attrs.define(kw_only=True)
class SoftwareRevisionInvalidError(codec.BaseCodecError):  # noqa: D101
    revision_string: str

    def __str__(self) -> str:  # noqa: D105
        return f"Software revision string {self.revision_string!r} is invalid."


@attrs.define(kw_only=True)
class SerialNumberInvalidError(codec.BaseCodecError):  # noqa: D101
    serial: str

    def __str__(self) -> str:  # noqa: D105
        return f"Serial {self.serial!r} is invalid; should contain digits only."


class HasCommandIdAndName(Protocol):  # noqa: D101
    command_id: ClassVar[int]
    command_name: ClassVar[str]

    @classmethod
    def _decode_validate_command_id(cls, command_id: int) -> None:
        if command_id != cls.command_id:
            raise MessageCidMismatchError(
                actual=command_id,
                cid_expected=cls.command_id,
                message_class_name=cls.__name__,
            )


class BaseRequest(HasCommandIdAndName, Protocol[Res_t_co]):
    """
    Base protocol for any message that is a request (client to meter).

    Generically type-annotated for the response type matching the request.
    """

    response_type: ClassVar[type]

    @classmethod
    def get_response_type(cls) -> type[Res_t_co]:
        """Return the response class (type) matching this request class."""
        return cls.response_type  # pyright: ignore[reportGeneralTypeIssues]


class BaseResponse(HasCommandIdAndName, Protocol[Req_t_co]):
    """
    Base protocol for any message that is a response (meter to client).

    Generically type-annotated for the request type matching the response.
    """

    request_type: ClassVar[type]

    @classmethod
    def get_request_type(cls) -> type[Req_t_co]:
        """Return the request class (type) matching this response class."""
        return cls.request_type  # pyright: ignore[reportGeneralTypeIssues]


class SupportsDecode(Protocol):
    """Base protocol to indicate it supports decoding (has decode() class method)."""

    @classmethod
    def decode(cls, data: codec.ApplicationData) -> Self:
        """Decode application data to structured message instance (of type itself)."""
        ...  # pragma: no cover


class SupportsEncode(Protocol):
    """Base protocol to indicate it supports encoding (has encode() class method)."""

    def encode(self) -> codec.ApplicationData:
        """Encode itself (structured message instance) to application data."""
        ...  # pragma: no cover


class WithoutDataMixin(HasCommandIdAndName, SupportsDecode, SupportsEncode, Protocol):
    """Helper base class for messages that do not hold any data aside the command ID."""

    @classmethod
    def decode(cls, data: codec.ApplicationData) -> Self:
        """Decode the message (command ID only, no data expected for this message)."""
        cls._decode_validate_command_id(data.command_id)
        if data.data:
            raise DataWithNoDataError(message_class=cls)
        return cls()

    def encode(self) -> codec.ApplicationData:
        """Encode the message (command ID only, no data expected for this message)."""
        return codec.ApplicationData(
            command_id=self.command_id, data=codec.ApplicationDataBytes(b"")
        )


@attrs.define(auto_attribs=False, slots=False, kw_only=True)
class WithDataMixin(HasCommandIdAndName, Protocol):
    """Protocol with 'data_raw' attribute to reference the pre-decoded original data."""

    # Set only on instantiation via decode().
    data_raw: codec.ApplicationDataBytes | None = attrs.field(default=None)


@attrs.define(auto_attribs=False, slots=False, kw_only=True)
class GetTypeRequest(
    BaseRequest["GetTypeResponse"],
    WithoutDataMixin,
):
    """Request the meter type and software revision."""

    response_type: ClassVar[type[GetTypeResponse]]
    command_id: ClassVar[int] = constants.CommandId.GET_TYPE.value
    command_name: ClassVar[str] = "GetType"


@attrs.define(auto_attribs=False, slots=False, kw_only=True)
class GetTypeResponse(
    BaseResponse[GetTypeRequest],
    WithDataMixin,
    SupportsDecode,
    SupportsEncode,
):
    """Response with the meter type and its software revision."""

    request_type: ClassVar[type] = GetTypeRequest
    command_id: ClassVar[int] = GetTypeRequest.command_id
    command_name: ClassVar[str] = GetTypeRequest.command_name

    # format: 2x2=4 bytes, binary encoded. TODO: Try to decode details.
    meter_type_bytes: bytes = attrs.field()
    # format: one letter followed by 1-3 digits. May not be available on all meters.
    # instead, it may be available in register 1005 (decimal) using the GetRegister
    # command.
    software_revision: str | None = attrs.field()

    # defined as 16 bits (6.2.1 Kamstrup KMP description document).
    METER_TYPE_LENGTH_ENCODED: ClassVar[int] = 2
    # defined as 16 bits (6.2.1 Kamstrup KMP description document).
    SOFTWARE_REVISION_LENGTH_ENCODED: ClassVar[int] = 2
    SOFTWARE_REVISION_LETTER_INT_MIN: ClassVar[int] = 1
    SOFTWARE_REVISION_LETTER_INT_MAX: ClassVar[int] = 26
    SOFTWARE_REVISION_STR_RE: ClassVar[re.Pattern[str]] = re.compile(
        rf"^(?P<letter>[A-Z])(?P<number>{ZERO_TO_255_RE.pattern})$",
        re.VERBOSE,
    )
    SOFTWARE_REVISION_UNAVAILABLE_BYTES: ClassVar[bytes] = b"\x00\x00"

    @classmethod
    def decode(cls, data: codec.ApplicationData) -> Self:
        """Decode GetType response."""
        cls._decode_validate_command_id(data.command_id)
        length_expected = (
            cls.METER_TYPE_LENGTH_ENCODED + cls.SOFTWARE_REVISION_LENGTH_ENCODED
        )
        data_len = len(data.data)
        logger.debug(
            "Decoding GetType data. [len=%d, expected_len=%d, data=%r]",
            data_len,
            length_expected,
            data.data.hex().upper(),
        )
        if data_len != length_expected:
            raise codec.DataLengthUnexpectedError(
                what="GetType response data",
                length_expected=length_expected,
                actual=data_len,
            )

        meter_type_bytes, sw_rev_bytes = data.data[:2], data.data[2:]
        if sw_rev_bytes == cls.SOFTWARE_REVISION_UNAVAILABLE_BYTES:
            software_revision = None
        else:
            # The letter is encoded like 0x01=A and 0x02=B, etc.
            sw_rev_letter_int = sw_rev_bytes[0]
            if not (
                cls.SOFTWARE_REVISION_LETTER_INT_MIN
                <= sw_rev_letter_int
                <= cls.SOFTWARE_REVISION_LETTER_INT_MAX
            ):
                logger.debug(
                    "Decoding %s response; software revision letter out of range. "
                    "[data=%r]",
                    cls.command_name,
                    data.data.hex().upper(),
                )
                valid_range = (
                    cls.SOFTWARE_REVISION_LETTER_INT_MIN,
                    cls.SOFTWARE_REVISION_LETTER_INT_MAX,
                )
                raise codec.OutOfRangeError(
                    what="Software revision letter (int value)",
                    valid_range=valid_range,
                    actual=sw_rev_letter_int,
                )
            sw_rev_letter = chr(sw_rev_letter_int + 64)
            sw_rev_number = sw_rev_bytes[1]
            software_revision = f"{sw_rev_letter}{sw_rev_number}"

        return cls(
            meter_type_bytes=meter_type_bytes,
            software_revision=software_revision,
            data_raw=data.data,
        )

    def encode(self) -> codec.ApplicationData:
        """Encode GetType response."""
        logger.debug(
            "Encoding %s response [meter_type_bytes=%r, software_revision=%s]",
            self.command_name,
            self.meter_type_bytes.hex().upper(),
            self.software_revision,
        )
        if len(self.meter_type_bytes) != self.METER_TYPE_LENGTH_ENCODED:
            raise codec.DataLengthUnexpectedError(
                what=f"{self.__class__.__name__} meter type bytes",
                length_expected=self.METER_TYPE_LENGTH_ENCODED,
                actual=len(self.meter_type_bytes),
            )

        if self.software_revision is None:
            sw_rev_bytes = self.SOFTWARE_REVISION_UNAVAILABLE_BYTES
        else:
            if not (
                matches := self.SOFTWARE_REVISION_STR_RE.match(self.software_revision)
            ):
                raise SoftwareRevisionInvalidError(
                    revision_string=self.software_revision
                )
            sw_rev_letter, sw_rev_number = matches["letter"], matches["number"]
            sw_rev_letter_bytes = (ord(sw_rev_letter) - 64).to_bytes(1, "big")
            sw_rev_number_bytes = int(sw_rev_number).to_bytes(1, "big")
            sw_rev_bytes = sw_rev_letter_bytes + sw_rev_number_bytes

        app_bytes = self.meter_type_bytes + sw_rev_bytes
        return codec.ApplicationData(
            command_id=self.command_id, data=codec.ApplicationDataBytes(app_bytes)
        )


GetTypeRequest.response_type = GetTypeResponse


@attrs.define(auto_attribs=False, slots=False, kw_only=True)
class GetSerialRequest(BaseRequest["GetSerialResponse"], WithoutDataMixin):
    """Request the meter's serial number."""

    response_type: ClassVar[type[GetSerialResponse]]
    command_id: ClassVar[int] = constants.CommandId.GET_SERIAL.value
    command_name: ClassVar[str] = "GetSerialNo"


@attrs.define(auto_attribs=False, slots=False, kw_only=True)
class GetSerialResponse(
    BaseResponse[GetSerialRequest],
    WithDataMixin,
    SupportsDecode,
    SupportsEncode,
):
    """Response with the serial number of the meter."""

    request_type: ClassVar[type]
    command_id: ClassVar[int] = GetSerialRequest.command_id
    command_name: ClassVar[str] = GetSerialRequest.command_name

    serial: str = attrs.field()

    # defined as 32 bits (6.2.2 Kamstrup KMP description document).
    SERIAL_LENGTH_ENCODED: ClassVar[int] = 4
    SERIAL_VALUE_MAX: ClassVar[int] = (2 ** (SERIAL_LENGTH_ENCODED * 8)) - 1

    @serial.validator  # pyright: ignore[reportUnknownMemberType, reportUntypedFunctionDecorator, reportGeneralTypeIssues]
    def digits_only_validator(self, _: attrs.Attribute[Self], value: str) -> None:
        """Validate all characters in string of serial number are digits."""
        try:
            int_value = int(value)
        except ValueError as exc:
            raise SerialNumberInvalidError(serial=value) from exc
        else:
            if not (0 <= int_value <= self.SERIAL_VALUE_MAX):
                raise codec.OutOfRangeError(
                    what="Serial number",
                    valid_range=(0, self.SERIAL_VALUE_MAX),
                    actual=int_value,
                )

    @classmethod
    def decode(cls, data: codec.ApplicationData) -> Self:
        """Decode GetSerialNo response."""
        cls._decode_validate_command_id(data.command_id)
        logger.debug(
            "Decoding %s data (len=%d != %d): %r",
            cls.command_name,
            len(data.data),
            cls.SERIAL_LENGTH_ENCODED,
            data.data.hex().upper(),
        )
        if len(data.data) != cls.SERIAL_LENGTH_ENCODED:
            raise codec.DataLengthUnexpectedError(
                what="Serial data",
                length_expected=cls.SERIAL_LENGTH_ENCODED,
                actual=len(data.data),
            )
        serial_int = int.from_bytes(data.data, "big")
        return cls(serial=str(serial_int), data_raw=data.data)

    def encode(self) -> codec.ApplicationData:
        """Encode GetSerialNo response."""
        # Should never fail with validator guarding bounds of 'serial'.
        serial_bytes = int(self.serial).to_bytes(self.SERIAL_LENGTH_ENCODED, "big")
        return codec.ApplicationData(
            command_id=self.command_id, data=codec.ApplicationDataBytes(serial_bytes)
        )


GetSerialRequest.response_type = GetSerialResponse


RegisterID = NewType("RegisterID", int)
RegisterUnit = NewType("RegisterUnit", int)
RegisterValueBytes = NewType("RegisterValueBytes", bytes)


def _ints2register_ids(
    # Also includes RegisterID here in union, because it overrides the type annotation
    # in __init__. (https://www.attrs.org/en/stable/init.html#converters)
    val: Collection[int | RegisterID],
) -> Collection[RegisterID]:
    return [RegisterID(rid) for rid in val]


@attrs.frozen(kw_only=True)
class RegisterData:
    """Partially decoded register data."""

    id_: RegisterID
    unit: RegisterUnit

    # decoding depends on register id and/or unit, e.g. a floating point decimal.
    value: RegisterValueBytes


@attrs.define(auto_attribs=False, slots=False, kw_only=True)
class GetRegisterRequest(
    BaseRequest["GetRegisterResponse"],
    WithDataMixin,
    SupportsDecode,
    SupportsEncode,
):
    """Request register values."""

    response_type: ClassVar[type[GetRegisterResponse]]
    command_id: ClassVar[int] = constants.CommandId.GET_REGISTER.value
    command_name: ClassVar[str] = "GetRegister"

    registers: Collection[RegisterID] = attrs.field(converter=_ints2register_ids)

    NUM_REGISTERS_LENGTH_ENCODED: ClassVar[int] = 1
    NUM_REGISTERS_MAX: ClassVar[int] = 8
    REGISTER_ID_LENGTH_ENCODED: ClassVar[int] = 2
    REGISTER_ID_VALUE_MAX: ClassVar[int] = (2 ** (REGISTER_ID_LENGTH_ENCODED * 8)) - 1

    @registers.validator  # pyright: ignore[reportUnknownMemberType, reportUntypedFunctionDecorator, reportGeneralTypeIssues]
    def register_id_validator(
        self, _: attrs.Attribute[Self], value: Collection[RegisterID]
    ) -> None:
        """Validate all register IDs in collection requested are within valid range."""
        for reg_id in value:
            if not (0 <= reg_id <= self.REGISTER_ID_VALUE_MAX):
                raise codec.OutOfRangeError(
                    what="Register ID",
                    valid_range=(0, self.REGISTER_ID_VALUE_MAX),
                    actual=reg_id,
                )

    @classmethod
    def _decode_register_ids_array(
        cls, *, num_registers: int, packed: bytes
    ) -> list[RegisterID]:
        expected_length = num_registers * cls.REGISTER_ID_LENGTH_ENCODED
        if (packed_len := len(packed)) != expected_length:
            logger.debug(
                "%s: Unexpected number of bytes for register IDs (len=%d != %d, "
                "num_registers=%d): %r",
                cls.command_name,
                packed_len,
                expected_length,
                num_registers,
                packed.hex().upper(),
            )
            what = f"{cls.command_name} request data for {num_registers} register ID(s)"
            raise codec.DataLengthUnexpectedError(
                what=what, length_expected=expected_length, actual=packed_len
            )
        registers_bytes = [
            packed[i : i + cls.REGISTER_ID_LENGTH_ENCODED]
            for i in range(0, packed_len, cls.REGISTER_ID_LENGTH_ENCODED)
        ]
        return [
            cast(RegisterID, int.from_bytes(register_id_bytes, "big"))
            for register_id_bytes in registers_bytes
        ]

    @classmethod
    def decode(cls, data: codec.ApplicationData) -> Self:
        """Decode GetRegister request."""
        cls._decode_validate_command_id(data.command_id)

        # case of zero registers requested is checked below
        min_length = cls.NUM_REGISTERS_LENGTH_ENCODED
        if (data_len := len(data.data)) < min_length:
            logger.debug(
                "Decoding %s data (len=%d < %d): %r",
                cls.command_name,
                data_len,
                min_length,
                data.data.hex().upper(),
            )
            raise codec.DataLengthUnexpectedError(
                what=f"{cls.command_name} request data",
                length_expected=min_length,
                expected_is_minimum=True,
                actual=data_len,
            )

        num_registers, registers_bytes = data.data[0], data.data[1:]
        if not (1 <= num_registers <= cls.NUM_REGISTERS_MAX):
            logger.warning(
                "Number of registers (%d) in %s request is outside the defined "
                "range (1-%d).",
                num_registers,
                cls.command_name,
                cls.NUM_REGISTERS_MAX,
            )

        registers = cls._decode_register_ids_array(
            num_registers=num_registers, packed=registers_bytes
        )
        return cls(registers=registers, data_raw=data.data)

    def encode(self) -> codec.ApplicationData:
        """Encode GetRegister request."""
        # Not in the attribute validator, as it's perfectly OK for a response to violate
        # the checks below.
        if not (1 <= (num_registers := len(self.registers)) <= self.NUM_REGISTERS_MAX):
            raise codec.OutOfRangeError(
                what=f"Number of registers requested in {self.command_name} request",
                valid_range=(1, self.NUM_REGISTERS_MAX),
                actual=num_registers,
            )

        num_registers_bytes = len(self.registers).to_bytes(
            self.NUM_REGISTERS_LENGTH_ENCODED, "big"
        )
        register_ids_bytes = b"".join(
            register_id.to_bytes(self.REGISTER_ID_LENGTH_ENCODED, "big")
            for register_id in self.registers
        )

        return codec.ApplicationData(
            command_id=self.command_id,
            data=codec.ApplicationDataBytes(num_registers_bytes + register_ids_bytes),
        )


@attrs.define(auto_attribs=False, slots=False, kw_only=True)
class GetRegisterResponse(
    BaseResponse[GetRegisterRequest],
    WithDataMixin,
    SupportsDecode,
    SupportsEncode,
):
    """Response with register value(s)."""

    request_type: ClassVar[type] = GetRegisterRequest
    command_id: ClassVar[int] = GetRegisterRequest.command_id
    command_name: ClassVar[str] = GetRegisterRequest.command_name

    registers: Mapping[RegisterID, RegisterData] = attrs.field(factory=dict)

    REGISTER_ID_LENGTH_ENCODED: ClassVar[int] = 2
    REGISTER_UNIT_LENGTH_ENCODED: ClassVar[int] = 1
    REGISTER_VALUE_LENGTH_LENGTH_ENCODED: ClassVar[int] = 1
    REGISTER_VALUE_FORMAT_LENGTH_ENCODED: ClassVar[int] = 1

    @classmethod
    def _decode_one_register_value(
        cls, raw: codec.ApplicationDataBytes
    ) -> tuple[RegisterData, codec.ApplicationDataBytes]:
        len_min = (
            cls.REGISTER_ID_LENGTH_ENCODED
            + cls.REGISTER_UNIT_LENGTH_ENCODED
            + cls.REGISTER_VALUE_LENGTH_LENGTH_ENCODED
            + cls.REGISTER_VALUE_FORMAT_LENGTH_ENCODED
            + 1
        )
        logger.debug(
            "Decoding register bytes. [raw=%r, length_min=%d]",
            raw.hex().upper(),
            len_min,
        )

        if (len_raw := len(raw)) < len_min:
            raise codec.DataLengthUnexpectedError(
                what="Data to decode register data",
                length_expected=len_min,
                expected_is_minimum=True,
                actual=len_raw,
            )

        # length byte excludes the sign+exponent byte
        value_length = raw[3] + cls.REGISTER_VALUE_FORMAT_LENGTH_ENCODED

        if not len_raw >= (expected_len_min := (4 + value_length)):
            raise codec.DataLengthUnexpectedError(
                what="Register value data left in buffer",
                length_expected=expected_len_min,
                expected_is_minimum=True,
                actual=len_raw,
            )

        data = RegisterData(
            id_=cast(RegisterID, int.from_bytes(raw[:2], "big")),
            unit=cast(RegisterUnit, raw[2]),
            value=cast(
                RegisterValueBytes,
                # length byte excludes the sign+exponent byte and include the length
                # byte itself too.
                raw[3 : 3 + value_length + cls.REGISTER_VALUE_LENGTH_LENGTH_ENCODED],
            ),
        )

        remaining_bytes = cast(codec.ApplicationDataBytes, raw[4 + value_length :])
        if 0 < (len_remaining := len(remaining_bytes)) < len_min:
            logger.warning(
                "Remaining data after decoding register value is unexpectedly short. "
                "[len=%d, min=%d]",
                len_remaining,
                len_min,
            )
        return data, remaining_bytes

    @classmethod
    def decode(cls, data: codec.ApplicationData) -> Self:
        """Decode the GetRegister response."""
        cls._decode_validate_command_id(data.command_id)
        bytes_remaining = data.data
        registers: dict[RegisterID, RegisterData] = {}
        while bytes_remaining:
            register_data, bytes_remaining = cls._decode_one_register_value(
                bytes_remaining
            )
            logger.debug(
                "Decoded register values: [id=%d, unit=%d, value_bytes=%s, "
                "remaining bytes=%d]",
                register_data.id_,
                register_data.unit,
                register_data.value.hex().upper(),
                len(bytes_remaining),
            )
            if register_data.id_ in registers:
                logger.warning(
                    "Duplicate register ID %d in response, overwriting value.",
                    register_data.id_,
                )
            registers.update({register_data.id_: register_data})
        return cls(registers=registers, data_raw=data.data)

    @classmethod
    def _encode_one_register_value(cls, data: RegisterData) -> bytes:
        id_bytes = data.id_.to_bytes(2, "big")
        unit_bytes = data.unit.to_bytes(1, "big")
        return id_bytes + unit_bytes + data.value

    def encode(self) -> codec.ApplicationData:
        """Encode the GetRegister response."""
        to_return = b"".join(
            self._encode_one_register_value(register)
            for register in self.registers.values()
        )

        return codec.ApplicationData(
            command_id=self.command_id,
            data=cast(codec.ApplicationDataBytes, to_return),
        )


GetRegisterRequest.response_type = GetRegisterResponse
