<!--
SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>

SPDX-License-Identifier: Apache-2.0
-->

# PyKMP – a Kamstrup meter toolset

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

**More info in the docs: [https://gertvdijk.github.io/PyKMP/][docs-home].**

[docs-home]: https://gertvdijk.github.io/PyKMP/
