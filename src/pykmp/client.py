# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

"""
Convenience in client communication with the KMP protocol (to meter).

The [PySerialClientCommunicator][pykmp.client.PySerialClientCommunicator] provides the
most high-level class to communicate with the meter.
"""

from __future__ import annotations

import importlib.util
import logging
from typing import Any, ClassVar, Generic, Protocol, TypeVar, cast

import attrs

from . import codec, constants, messages

PYSERIAL_AVAILABLE = bool(importlib.util.find_spec("serial"))


logger = logging.getLogger(__name__)

CCReq_t_co = TypeVar("CCReq_t_co", bound="ClientContextRequest[Any]", covariant=True)
CCResp_t_co = TypeVar("CCResp_t_co", bound="ClientContextResponse[Any]", covariant=True)


class ClientContextRequest(
    messages.SupportsEncode,
    messages.BaseRequest[CCResp_t_co],
    Protocol[CCResp_t_co],
):
    """Generic request KMP message type that can be used in a client context."""


class ClientContextResponse(
    messages.SupportsDecode,
    messages.BaseResponse[CCReq_t_co],
    Protocol[CCReq_t_co],
):
    """Generic response KMP message type that can be used in a client context."""


@attrs.define(kw_only=True)
class EncodedClientRequest(Generic[CCReq_t_co]):
    """Wraps the physical bytes type to include request type information."""

    physical_bytes: codec.PhysicalBytes
    request_cls: type[ClientContextRequest[ClientContextResponse[CCReq_t_co]]]


@attrs.define(kw_only=True)
class EncodedClientResponse(Generic[CCReq_t_co]):
    """Wraps the physical bytes type to include request (response) type information."""

    physical_bytes: codec.PhysicalBytes
    request_cls: type[CCReq_t_co]


DESTINATION_ADDRESS_DEFAULT = constants.DestinationAddress.HEAT_METER.value


@attrs.define(kw_only=True, auto_attribs=False)
class ClientCodec:
    """Wires up the codecs of all layers for communication *to the meter*."""

    destination_address: int = attrs.field(default=DESTINATION_ADDRESS_DEFAULT)
    application_codec: codec.ApplicationCodec = attrs.field(
        factory=codec.ApplicationCodec
    )
    data_link_codec: codec.DataLinkCodec = attrs.field(factory=codec.DataLinkCodec)
    physical_codec_encode: ClassVar = codec.PhysicalCodec(
        direction=codec.PhysicalDirection.TO_METER
    )
    physical_codec_decode: ClassVar = codec.PhysicalCodec(
        direction=codec.PhysicalDirection.FROM_METER
    )

    def encode(
        self, request: ClientContextRequest[ClientContextResponse[CCReq_t_co]]
    ) -> EncodedClientRequest[CCReq_t_co]:
        """Encode a request message to bytes for sending on the physical layer."""
        application_data = request.encode()
        application_bytes = self.application_codec.encode(application_data)
        data_link_data = codec.DataLinkData(
            destination_address=self.destination_address,
            application_bytes=application_bytes,
        )
        data_link_bytes = self.data_link_codec.encode(data_link_data)
        thebytes = self.physical_codec_encode.encode(data_link_bytes)
        return EncodedClientRequest(physical_bytes=thebytes, request_cls=type(request))

    def decode(
        self,
        *,
        frame: EncodedClientResponse[ClientContextRequest[CCResp_t_co]],
    ) -> CCResp_t_co:
        """Decode bytes from the physical layer to a response message."""
        try:
            data_link_bytes = self.physical_codec_decode.decode(frame.physical_bytes)
        except codec.AckReceivedException as exc:
            raise NotImplementedError from exc

        data_link_data = self.data_link_codec.decode(data_link_bytes)
        application_data = self.application_codec.decode(
            data_link_data.application_bytes
        )
        return frame.request_cls.get_response_type().decode(application_data)


class ClientCommunicator(Protocol):
    """Wrap the codecs and communication communication with the meter."""

    def read(self, *, num_bytes: int | None = None) -> codec.PhysicalBytes:
        """
        Read num_bytes number of bytes (or until stop byte if None) from [...].

        If num_bytes is provided, it reads num_bytes number of bytes, else it will
        read until stop byte.
        """
        ...  # pragma: no cover

    def write(self, data: codec.PhysicalBytes) -> None:
        """Write the bytes to [...]."""
        ...  # pragma: no cover

    def send_request(
        self,
        *,
        message: ClientContextRequest[CCResp_t_co],
        destination_address: int = DESTINATION_ADDRESS_DEFAULT,
    ) -> CCResp_t_co:
        """Encode and send a request, return decoded response."""
        client_codec = ClientCodec(destination_address=destination_address)
        wrapped_request_physical_bytes = client_codec.encode(message)
        request_physical_bytes = wrapped_request_physical_bytes.physical_bytes
        logger.debug("Request encoded: %s", request_physical_bytes.hex().upper())

        logger.info("Sending %s...", message.__class__.__name__)
        self.write(request_physical_bytes)

        response_physical_bytes = self.read()
        logger.debug(
            "Received bytes on serial: %r", response_physical_bytes.hex().upper()
        )

        wrapped_frame = EncodedClientResponse(
            physical_bytes=response_physical_bytes,
            request_cls=type(message),
        )
        return client_codec.decode(frame=wrapped_frame)


if PYSERIAL_AVAILABLE:
    import serial
    import serial.serialutil

    @attrs.define(kw_only=True, auto_attribs=False, slots=False)
    class PySerialClientCommunicator(ClientCommunicator):
        """
        Uses PySerial to connect, read and write to a meter.

        For connecting over TCP (e.g. with ser2net) use 'socket://<host>:<port>' as
        'serial_device' string.
        """

        DEFAULT_READ_TIMEOUT_SECONDS: ClassVar[float] = 2.0
        serial_device: str = attrs.field()
        timeout_seconds: float = attrs.field(default=DEFAULT_READ_TIMEOUT_SECONDS)

        def __attrs_post_init__(self) -> None:
            """Initialize a serial.Serial object in self._serial."""
            try:
                self._serial = serial.serial_for_url(
                    self.serial_device,
                    timeout=self.timeout_seconds,
                    baudrate=1200,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_TWO,
                )
            except serial.serialutil.SerialException:
                logger.exception(
                    "Could not set up serial communication with device %s.",
                    self.serial_device,
                )
                raise

        def read(self, *, num_bytes: int | None = None) -> codec.PhysicalBytes:
            """
            Read from serial device or network socket.

            If num_bytes is provided, it reads num_bytes number of bytes, else it will
            read until stop byte.
            """
            if num_bytes is None:
                return_bytes = self.read_until_stop()
            else:
                return_bytes = self.read_num_bytes(num_bytes)
            if not return_bytes:
                msg = (
                    f"Did not receive any bytes within {self.timeout_seconds} seconds."
                )
                raise TimeoutError(msg)
            return return_bytes

        def read_num_bytes(self, num_bytes: int) -> codec.PhysicalBytes:
            """Read num_bytes number of bytes from serial device or network socket."""
            return cast(codec.PhysicalBytes, self._serial.read(num_bytes))

        def read_until_stop(self) -> codec.PhysicalBytes:
            """Read bytes from serial device or network socket until a stop byte."""
            received_so_far = b""
            while received := self._serial.read():
                received_so_far += received
                if received == constants.ByteCode.STOP.value.to_bytes(1, "big"):
                    break
            return cast(codec.PhysicalBytes, received_so_far)

        def write(self, data: codec.PhysicalBytes) -> None:
            """Write the bytes to the serial device or network socket."""
            self._serial.write(data)
