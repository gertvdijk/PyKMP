# Getting started 🚀
<!--
SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>

SPDX-License-Identifier: CC0-1.0
-->

## Installation

First of all, you'll need Python 3.10+ (sorry, using modern Python features).

Then just install [`PyKMP` from :fontawesome-brands-python: PyPI][pypi-pykmp], e.g.:

```console
$ python -m venv /tmp/venv       #(1)
$ source /tmp/venv/bin/activate  #(2)
$ pip install -U pip setuptools  #(3)
$ {==pip install PyKMP==}[tool]        #(4)
```

1. Creates a 'virtual environment' using the Python built-in
    ['venv' module][python-docs-venv].

2. Run this every time in a new session to activate this virtual environment.

3. Not strictly needed, but generally a good idea to update core tools like setuptools
    and pip.

4. Install with the optional dependencies for the CLI tool by adding `[tool]`.

## CLI tool `pykmp-tool`

Let's explore some of the features by using the CLI tool first.

```console
$ source venv/bin/activate  # activate this venv in every new session
```
??? note "Full output of `pykmp-tool --help`"
    ```
    Usage: pykmp-tool [OPTIONS] COMMAND [ARGS]...

    Command line tool to request data from a Kamstrup meter.

    Options:
    -d, --serial-device TEXT        The path to the serial device, e.g. the USB-
                                    to-Serial converter on '/dev/ttyUSB0'. You
                                    may want to select a stable device path in
                                    '/dev/serial/by-id/' instead.

                                    For connecting over TCP (e.g. with ser2net),
                                    you can use 'socket://<host>:<port>'.  [env
                                    var: PYKMP_SERIAL_DEVICE; default:
                                    /dev/ttyUSB0]
    -a, --destination-address DEC_OR_HEX
                                    Data link layer destination address. (hex or
                                    int)

                                    The default is set to 63 (HEAT_METER). Other
                                    known addresses: 127 (LOGGER_TOP), 191
                                    (LOGGER_BASE)

                                    ⚠ The tool has only been tested with the
                                    default value.  [env var:
                                    PYKMP_DESTINATION_ADDRESS; default: 63]
    -v, --verbose                   Show more logging (twice for debug logging)
                                    [default: 0]
    --help                          Show this message and exit.

    Commands:
    get-register  Request register(s) of the Kamstrup meter and print the...
    get-serial    Request the serial number of a Kamstrup meter and print it.
    ```

Retrieve some interesting metrics (registers):

```console
$ export PYKMP_SERIAL_DEVICE=/dev/ttyUSB0  #(1)
$ pykmp-tool get-register \
    --register 60 \
    --register 68 \
    --register 80 \
    --register 74 \
    --register 86 \
    --register 87 \
    --register 266
GetRegister response(s):
  60 → Heat Energy (E1) = 0.303 GJ
  68 → Volume           = 11.388 m³
  80 → Current Power    = 0.0 kW
  74 → Flow             = 3 l/h
  86 → Temp1            = 61.62 °C
  87 → Temp2            = 54.02 °C
 266 → E1HighRes        = 84208 Wh
```

1. Totally optional, but here we use an environment variable for convenience instead of
   `--serial-device /dev/ttyUSB0` in the command.
    You just have to set (export) it once for the session.

    :bulb: See `pykmp-tool --help` for how any other command line option can be set with
    environment variables.

!!! tip

    Add `--json` to get structured machine-readable output in JSON format.

In case you run into issues...

```console
$ pykmp-tool get-register --register 1002
WARNING:pykmp.tool.__main__:Unknown register ID(s); please report this if you have more information.
GetRegister response(s):
1002 → <unknown reg 1002> = 200132 hh:mm:ss
```
... you may want to show more verbose logging and debug the communication by adding
`-vv`:

```console
$ pykmp-tool {==-vv==} get-register --register 1002
DEBUG:pykmp.client:Request encoded: 803F100103EA4CB70D
INFO:pykmp.client:Sending GetRegisterRequest...
DEBUG:pykmp.client:Received bytes on serial: '403F1003EA2F040000030E33B2320D'
DEBUG:pykmp.codec:Checksum verification OK [raw=3f1003ea2f040000030e33b232, crc_given=b232, crc_calculated=OK]
DEBUG:pykmp.messages:Decoding register bytes. [raw='03EA2F040000030E33', length_min=6]
DEBUG:pykmp.messages:Decoded register values: [id=1002, unit=47, value_bytes=040000030E33, remaining bytes=0]
WARNING:pykmp.tool.__main__:Unknown register ID(s); please report this if you have more information.
GetRegister response(s):
DEBUG:pykmp.codec:Decoding parts of floating point data. [data='040000030E33', integer_length=4]
DEBUG:pykmp.codec:Decoded floating point data: Decimal('200243') [data='040000030E33', man=200243, si=False, se=False, exp=0]
1002 → <unknown reg 1002> = 200243 hh:mm:ss
```

Clearly, some registers appear undiscovered and the formatting for some units need some
love. 😅

So far we've only seen 'GetRegister' commands/responses.
Another command is 'GetSerialNo':

```console
$ pykmp-tool get-serial
Meter serial is: 123456
```

## API examples

To perform the above example with requesting the serial number, but then
programmatically using the API:

```{ .python .copy }
from pykmp import GetSerialRequest, PySerialClientCommunicator

multical = PySerialClientCommunicator(serial_device="/dev/ttyUSB0")
response = multical.send_request(message=GetSerialRequest())
print(f"Meter serial is: {response.serial}")
```

And similarly, for obtaining the register data:

```{ .python .copy }
from pykmp import (
    REGISTERS,
    UNITS_NAMES,
    FloatCodec,
    GetRegisterRequest,
    PySerialClientCommunicator,
)

multical = PySerialClientCommunicator(serial_device="/dev/ttyUSB0")
response = multical.send_request(
    message=GetRegisterRequest(registers=[60, 68, 74, 80, 86, 87, 89, 266])
)
for reg in response.registers.values():
    name, unit = REGISTERS.get(reg.id_, "?"), UNITS_NAMES.get(reg.unit, "?")
    print(f"Register {reg.id_} ({name}) data: {FloatCodec.decode(reg.value)} {unit}")
```

[python-docs-venv]: https://docs.python.org/3/library/venv.html
[pypi-pykmp]: https://pypi.org/project/PyKMP/
