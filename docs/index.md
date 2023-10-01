# PyKMP – a Kamstrup meter toolset
<!--
SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>

SPDX-License-Identifier: CC0-1.0
-->

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org/)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/en/stable/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json)](https://github.com/charliermarsh/ruff)
![100% test coverage](https://img.shields.io/badge/test_coverage-100%25-green)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-brightgreen)](https://www.apache.org/licenses/LICENSE-2.0)
[![REUSE compliant](https://img.shields.io/badge/reuse-compliant-brightgreen)](https://reuse.software/)

This module is developed for reading out Kamstrup meters using their vendor-specific KMP
protocol.

Tested with a MULTICAL® 403, based on documentation of the protocol for the older
MULTICAL® models.

Current state: *alpha* – based on the documentation it "should work" with a MULTICAL®
30x/40x/60x, but for other models: YMMV.
*Pull requests welcome!*

!!! note

    This project is not affiliated with Kamstrup A/S, Kamstrup B.V. or any other entity of
    the Kamstrup corporation.

!!! warning "Warning: battery consumption impact"

    Please be informed about the battery consumption impact, read the [battery consumption page](battery-consumption.md).

    Use at your own risk.

## Features ✨

*Note that this is a **library**, intended primarily for development or integration.*

- [x] A **bundled CLI tool** to interact with the meter for testing/development purposes
    with JSON format output (optional).
- [x] Read **multiple registers in one go** to conserve the meter's internal battery as
    much as possible.
- [x] Having it all **fully type-annotated** (mypy strict, zero `type: ignore`s) should
    make using this library a breeze.
- [x] **100% test coverage** (library, not the tool yet).
- [x] Ability to decode the base-10 variable length floating point values in registers
    **without loss of significance**.
- [x] **CRC checksum** verification (and adding).
- [x] Agnostic to the direction for message encoding, ie. you could go wild and
    **emulate a meter** using your IR optical head. 🤓

## License

The majority of the project is [Apache 2.0][apache-license-2] licensed.

Files deemed insignificant in terms of copyright such as configuration files are
licensed under the public domain "no rights reserved" [CC0] license.

The repository is [REUSE][reuse-home] compliant.

Read more on contributing in [Contributing][contributing.md].

*[YMMV]: your mileage may vary

[CC0]: https://creativecommons.org/share-your-work/public-domain/cc0/
[apache-license-2]: https://www.apache.org/licenses/LICENSE-2.0
[reuse-home]: https://reuse.software/
[contributing.md]: contributing.md
