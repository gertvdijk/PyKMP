<!--
SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>

SPDX-License-Identifier: Apache-2.0
-->

# PyKMP – a Kamstrup meter toolset

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org/)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/en/stable/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json)](https://github.com/charliermarsh/ruff)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-brightgreen)](https://www.apache.org/licenses/LICENSE-2.0)
[![REUSE compliant](https://img.shields.io/badge/reuse-compliant-brightgreen)](https://reuse.software/)

This module is developed for reading out Kamstrup meters using their vendor-specific KMP
protocol.

Tested with a MULTICAL® 403, based on documentation of the protocol for the older
MULTICAL® models.

Current state: *alpha* – based on the documentation it "should work" with a MULTICAL®
30x/40x/60x, but for other models: YMMV.
*Pull requests welcome!*

## Features ✨

*Note that this is a **library**, intended primarily for development or integration.*

- A **bundled CLI tool** to interact with the meter for testing/development purposes
  with JSON format output (optional).
- Read **multiple registers in one go** to conserve the meter's internal battery as much
  as possible.
- Having it all **fully type-annotated** (mypy strict, zero `type: ignore`s) should make
  using this library a breeze.
- **100% test coverage** (library, not the tool yet).
- Ability to decode the base-10 variable length floating point values in registers
  **without loss of significance**.
- **CRC checksum** verification (and adding).
- Agnostic to the direction for message encoding, ie. you could go wild and
  **emulate a meter** using your IR head. 🤓

## Hardware requirements

For software: Python 3.10+ (and some generic dependencies).

For most situation you would want to use the optical/infrared interface.
For that, you will need an IR optical read-out head with serial (or serial-to-USB)
interface.

Using
[Ali-Express: 'USB to optical interface IrDA near-infrared magnetic adapter'][ali-e-link-optical-head]
this is confirmed working with the MULTICAL® 403 (IR head positioned upside down).

## Getting started 🚀

> [!IMPORTANT]\
> This project is not affiliated with Kamstrup A/S, Kamstrup B.V. or any other entity of
> the Kamstrup corporation.
>
> Please be informed about the battery consumption impact, read the note below.
>
> Use at your own risk.

First of all, you'll need Python 3.10+ (sorry, using modern Python features).

Then just install `PyKMP' from PyPI, e.g.:

```
$ python -m venv /tmp/venv       # create a virtualenv
$ source /tmp/venv/bin/activate  # every time in a new session to activate this venv
$ pip install -U pip setuptools  # good idea to have an up-to-date pip & setuptools
$ pip install PyKMP[tool]        # install with CLI tool dependencies
```

> [!NOTE]\
> 💡 If you intend to make changes to the library itself, may want to pass the
> `--editable` option ['Development Mode'][pip-install-editable] to the last command.

Let's explore some of the features by using the CLI tool first.

```
$ source venv/bin/activate  # activate this venv in every new session
$ pykmp-tool --help
```

Retrieve some interesting metrics:

```
$ export PYKMP_SERIAL_DEVICE=/dev/ttyUSB0  # env var for convenience, less repetition
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

> [!NOTE]\
> 💡 Add `--json` to get structured machine-readable output.

Debug the communication and decoding using `-vv`:

```
$ pykmp-tool get-register --register 1002
WARNING:pykmp.tool.__main__:Unknown register ID(s); please report this if you have more information.
GetRegister response(s):
1002 → <unknown reg 1002> = 200132 hh:mm:ss

$ pykmp-tool -vv get-register --register 1002
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

So far we've only seen GetRegister commands/responses.
Another command is 'GetSerialNo':

```
$ pykmp-tool get-serial
Meter serial is: 123456
```

To do the above programmatically:

```python
from pykmp import GetSerialRequest, PySerialClientCommunicator

multical = PySerialClientCommunicator(serial_device="/dev/ttyUSB0")
response = multical.send_request(message=GetSerialRequest())
print(f"Meter serial is: {response.serial}")
```

And for the registers:

```python
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

## Store and graph metrics 📊

That's not really in scope of this library, but a separate project could (should) use
this library.

Anyway, it's planned to build that too!
`<img src="under-construction.gif">`

In the meantime, you could try to automate the output in JSON format using
`pykmp-tool get-register --json [...]`.

## Resources 📚

### KMP Protocol documentation

Technical description of meters sometimes show a little information of the design and
generic specification of the protocol.
This gives some clues about device-specific registers or a graphical explanation of the
OSI layers.
However, important details are in a separate document which is seemingly only available
under NDA. 😢

> **12.3 Data protocol**
>
> Utilities and other relevant companies who want to develop their own communication
> driver for the KMP protocol can order a demonstration program in C# (.net based) as
> well as a detailed protocol description (in English language).

Some more clues can be found in related communcation interfaces like MODBUS where
registers are listed:
[Modbus/KMP TCP/IP module for MULTICAL® 603 Data sheet][multical-hu-kmp-modbus-datasheet]

Nice people from the MeterLogger project have left [some notes][meterlogger-wiki-kmp]
for the development of the MeterLogger for Kamstrup meters.

Access to the vendor's own software to communicate with the meters ('Metertool HCW') is
not available (or at least not for free).

## Troubleshooting

### Unable to run the tool `pykmp-tool: command not found`

Using a Python package manager (e.g. pip) should ensure the entry point should be
installed somewhere in a directory that's on your PATH, but apparently that failed.

As an alternative, you can try to substitute `pykmp-tool` with `python -m pykmp.tool`.

### Unable to get a reading (connection timeout)

- Make sure your IR head has an included magnet that activates the meter's IR circuit.
  If in doubt, activate it by pressing any button and try to get a reading while the
  display is active.
- Make sure the RX/TX is aligned with the meter.
  It's most if not all cases the IR head has to be placed in upside-down position.
- Try to re-align around the position of the IR eye while keeping a command running in a
  loop in your shell.

## Other notes & TODOs ✍️

### Warning: battery consumption 🪫

Most Kamstrup meters for heat are battery-powered.
Using the optical/infrared interface will draw extra power from the battery and it may
deplete sooner when using this on a regular basis.

Extending the interval of reading should help, as well as requesting all data you need
in a single request (rather than looping).

Reading the battery level is not (yet) possible.

Some (older) models may require periodic re-activation of the IR-circuit.

### Connecting over the network (ser2net)

It's not always practical to communicate with the meter via (USB-to-)serial.
Using [ser2net][ser2net-github] on a (small) device close to the meter you can expose it
on your network.

Example configuration:

```yaml
connection: &mykamstrup
  accepter: tcp,2002
  connector: >-
    serialdev,
    /dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0,
    1200n82
  options:
    max-connections: 1
```

This above example uses TCP port 2002 on the host.
A connection can be made from any other host using:

```
$ pykmp-tool --serial-device socket://hostname:2002 [...]
```

Or use the environment variable to not having to specify it in every command:

```
$ export PYKMP_SERIAL_DEVICE=socket://hostname:2002
```

### Possible reading of higher resolution registers

In Kamstrup MULTICAL® 403 Technical description section
*11.3 Reading high resolution registers.* you'll find:

- E1ExtraDigit (9 digits instead of 8)
- E1HighRes ('internal' resolution, but truncated to include LSB)

It mentions kWh/Wh digits in that document, but the registers referred to can be
configured for MWh/GJ too, depending on the B-code (section 7.2). So, it may
work for configurations that display in GJ as well.

The register numbers and encodings aren't specified, though. However, the
MULTICAL® 302 Technical description section 13.1.1 mentions E1HighRes is
register ID 266 (decimal).

## Thanks to... 🙏

This project's existence is mainly thanks to all the information and regarding the KMP
protocol people have put online over the years.

As mentioned above, the MeterLogger project have left [some notes][meterlogger-wiki-kmp]
for the development of the MeterLogger for Kamstrup meters. Also the work by
Poul-Henning Kamp (and later Ronald van der Meer) in
[GitHub: `ronaldvdmeer/multical402-4-domoticz`][github-ronaldvdmeer-multical402]
was inspiring to get started with exploring possibilities and testing my hardware.

Finally, also a shoutout to the Dutch community Tweakers where a forum topic pointed out
the possibilities integrating these MULTICAL® meters (as provided by Dutch utilities) to
non-cloud smart home.
[GoT: Kamstrup Multical 402 stadsverwarmingsmeter RPI3+IR-kop][got-multical402-topic]

## License

The majority of the project is [Apache 2.0][apache-license-2] licensed.

Files deemed insignificant in terms of copyright such as configuration files are
licensed under the public domain "no rights reserved" [CC0] license.

The repository is [REUSE][reuse-home] compliant.

Read more on contributing in [CONTRIBUTING.md][contributing-md].

[ali-e-link-optical-head]: https://www.aliexpress.com/item/1005003509520122.html
[pip-install-editable]: https://setuptools.pypa.io/en/latest/userguide/development_mode.html
[multical-hu-kmp-modbus-datasheet]: https://www.multical.hu/upload/files/Modbus_KMP_TCP_IP.pdf
[ser2net-github]: https://github.com/cminyard/ser2net
[meterlogger-wiki-kmp]: https://github.com/nabovarme/MeterLogger/wiki/Kamstrup-Protocol
[github-ronaldvdmeer-multical402]: https://github.com/ronaldvdmeer/multical402-4-domoticz
[got-multical402-topic]: https://gathering.tweakers.net/forum/list_messages/1776625
[CC0]: https://creativecommons.org/share-your-work/public-domain/cc0/
[apache-license-2]: https://www.apache.org/licenses/LICENSE-2.0
[reuse-home]: https://reuse.software/
[contributing-md]: ./CONTRIBUTING.md
