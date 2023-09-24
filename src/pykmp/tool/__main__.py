# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import decimal
import json
import logging
from typing import TYPE_CHECKING, Any, Final

import attrs
import click

import pykmp
from pykmp import client, codec, constants, messages

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from typing_extensions import Self


logger = logging.getLogger(__name__)


class DecimalOrHexParamType(click.ParamType):
    """Converts Click command line parameter value to integer with support for hex."""

    name = "dec_or_hex"

    def convert(
        self,
        value: int | str,
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> int:
        if isinstance(value, int):
            return value

        try:
            # base=0 will auto-decode both "0xAB" and "123" strings to int with the
            # correct base.
            return int(value, base=0)
        except ValueError:
            self.fail(f"{value!r} is not a valid integer or hex", param, ctx)


DEC_OR_HEX = DecimalOrHexParamType()


ENV_VAR_PREFIX = pykmp.__name__.upper()


DESTINATION_ADDRESS_DEFAULT = attrs.fields(
    client.ClientCodec
).destination_address.default
DESTINATION_ADDRESSES_OTHER = [
    e for e in constants.DestinationAddress if e.value != DESTINATION_ADDRESS_DEFAULT
]
DESTINATION_ADDRESSES_OTHER_STR = ", ".join(
    f"{e.value} ({e.name})" for e in DESTINATION_ADDRESSES_OTHER
)


@attrs.frozen(kw_only=True)
class ClickContextObj:
    serial_device: str = attrs.field(default="/dev/ttyUSB0")
    destination_address: int = attrs.field(default=DESTINATION_ADDRESS_DEFAULT)


@click.group(
    context_settings={"show_default": True, "auto_envvar_prefix": ENV_VAR_PREFIX}
)
@click.option(
    "--serial-device",
    "-d",
    default=attrs.fields(ClickContextObj).serial_device.default,
    help=(
        """
        The path to the serial device, e.g. the USB-to-Serial converter on
        '/dev/ttyUSB0'. You may want to select a stable device path in
        '/dev/serial/by-id/' instead.

        For connecting over TCP (e.g. with ser2net), you can use
        'socket://<host>:<port>'.
        """
    ),
    show_envvar=True,
)
@click.option(
    "--destination-address",
    "-a",
    default=DESTINATION_ADDRESS_DEFAULT,
    help=(
        f"""
          Data link layer destination address. (hex or int)

          The default is set to {DESTINATION_ADDRESS_DEFAULT}
          ({constants.DestinationAddress(DESTINATION_ADDRESS_DEFAULT).name}).
          Other known addresses: {DESTINATION_ADDRESSES_OTHER_STR}

          \N{WARNING SIGN}
          The tool has only been tested with the default value.
          """
    ),
    show_envvar=True,
    type=DEC_OR_HEX,
)
@click.option(
    "-v", "--verbose", count=True, help="Show more logging (twice for debug logging)"
)
@click.pass_context
def main(
    ctx: click.Context, *, serial_device: str, destination_address: int, verbose: int
) -> None:
    """Command line tool to request data from a Kamstrup meter."""
    log_level = logging.WARNING
    if verbose == 1:
        log_level = logging.INFO
    elif verbose > 1:
        log_level = logging.DEBUG

    logging.basicConfig(level=log_level)
    ctx.obj = ClickContextObj(
        serial_device=serial_device,
        destination_address=destination_address,
    )


@main.command()
@click.pass_context
def get_serial(ctx: click.Context) -> None:
    """Request the serial number of a Kamstrup meter and print it."""
    common_options: ClickContextObj = ctx.obj
    communicator = client.PySerialClientCommunicator(
        serial_device=common_options.serial_device
    )  # pyright: ignore[reportGeneralTypeIssues]
    try:
        response = communicator.send_request(
            message=messages.GetSerialRequest(),
            destination_address=common_options.destination_address,
        )
    except TimeoutError:
        return

    click.echo(f"Meter serial is: {response.serial}")


REGISTERS_NAMES_LEN_MAX: Final[int] = max(
    len(name) for name in constants.REGISTERS.values()
)


@attrs.define(kw_only=True)
class RegisterOutput:
    id_int: int
    id_hex: str = attrs.field(init=False)
    name: str = attrs.field(init=False)
    unit_int: int
    unit_hex: str = attrs.field(init=False)
    unit_str: str = attrs.field(init=False)
    value_float: float = attrs.field(init=False)
    value_str: str = attrs.field(init=False)  # best: uses decimal.Decimal without loss
    value_dec: decimal.Decimal

    def __attrs_post_init__(self) -> None:
        self.id_hex = f"0x{self.id_int:04X}"
        self.unit_hex = f"0x{self.unit_int:02X}"
        self.name = constants.REGISTERS.get(self.id_int, f"<unknown reg {self.id_int}>")
        self.unit_str = constants.UNITS_NAMES.get(
            self.unit_int, f"<unknown unit {self.unit_int}>"
        )
        self.value_float = float(self.value_dec)
        self.value_str = str(self.value_dec)

    @classmethod
    def from_register_data(cls, reg: messages.RegisterData) -> Self:
        value_dec = codec.FloatCodec.decode(reg.value)
        return cls(
            id_int=reg.id_,
            unit_int=reg.unit,
            value_dec=value_dec,
        )

    def to_pretty_line(self) -> str:
        return (
            f"{self.id_int!r:>4} → {self.name:<{REGISTERS_NAMES_LEN_MAX}} = "
            f"{self.value_str} {self.unit_str}"
        )


def warn_registers_unknowns(
    registers: Collection[messages.RegisterData],
) -> None:
    if not {reg.unit for reg in registers} <= constants.UNITS_NAMES.keys():
        logger.warning(
            "Unknown unit(s) in output; please report this if you have more "
            "information. Optimistic value decoding as floating point may fail."
        )
    if not {reg.id_ for reg in registers} <= constants.REGISTERS.keys():
        logger.warning(
            "Unknown register ID(s); please report this if you have more information."
        )


GET_REGISTERS_ENV_VAR = f"{ENV_VAR_PREFIX}_GET_REGISTERS"


@main.command()
@click.option(
    "--register",
    type=DEC_OR_HEX,
    multiple=True,
    default=["60"],
    help=(
        f"""
        Register ID ([decimal] or 0x[hex]) to request. Repeat option for requesting
        multiple registers at once (recommended over looping, to conserve energy).

        If using the environment variable, use a space-separated string, e.g.:

        {GET_REGISTERS_ENV_VAR}='60 68 74 0x50 86 87 89 0x10A'

        Note that the meter may only allow for a maximum number of registers to request
        at once. It is currently limited here to
        {messages.GetRegisterRequest.NUM_REGISTERS_MAX}.
        """
    ),
    envvar=GET_REGISTERS_ENV_VAR,
    show_envvar=True,
)
@click.option(
    "--text",
    "output_format",
    flag_value="text",
    help="Output format: text to stdout",
    default=True,
)
@click.option(
    "--json", "output_format", flag_value="json", help="Output format: JSON to stdout"
)
@click.pass_context
def get_register(
    ctx: click.Context, *, register: Sequence[int], output_format: str
) -> None:
    """
    Request register(s) of the Kamstrup meter and print the response.

    For most MULTICAL® heat meters (tested on 403) you can try the following registers:

    \b
    60: heat energy total
    68: total volume
    74: current flow
    80: current power
    86: temperature in
    87: temperature out
    89: temperature difference
    266: high resolution heat energy (MSB truncated)

    If the meter does not include the register data in the response it means it's
    unavailable for the meter.
    """
    common_options: ClickContextObj = ctx.obj
    communicator = client.PySerialClientCommunicator(
        serial_device=common_options.serial_device
    )  # pyright: ignore[reportGeneralTypeIssues]
    request = messages.GetRegisterRequest(
        registers=[messages.RegisterID(rid) for rid in register]
    )
    try:
        response = communicator.send_request(
            message=request,
            destination_address=common_options.destination_address,
        )
    except TimeoutError:
        return

    warn_registers_unknowns(response.registers.values())
    outputs = (
        RegisterOutput.from_register_data(reg) for reg in response.registers.values()
    )

    match output_format:
        case "text":
            click.echo(f"{request.command_name} response(s):")
            for reg in outputs:
                click.echo(f"{reg.to_pretty_line()}")
        case "json":
            for_json: dict[str, list[Any]] = {
                "register_data": [
                    attrs.asdict(
                        reg,
                        # Filter non-JSON-serializable attributes
                        filter=attrs.filters.exclude(decimal.Decimal),
                    )
                    for reg in outputs
                ]
            }
            click.echo(json.dumps(for_json))
        case _:
            raise ValueError


if __name__ == "__main__":
    main()
