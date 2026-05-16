# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

"""PyKMP is a package to read and parse Kamstrup Multical energy meters."""

from __future__ import annotations

from .client import PYSERIAL_AVAILABLE, ClientCommunicator
from .codec import FloatCodec
from .constants import REGISTERS, UNITS_NAMES
from .messages import (
    GetRegisterRequest,
    GetRegisterResponse,
    GetSerialRequest,
    GetSerialResponse,
    GetTypeRequest,
    GetTypeResponse,
    RegisterData,
    RegisterID,
)

# `PySerialClientCommunicator` is intentionally not re-exported from the package root.
# Doing so would make the optional `pyserial` dependency an unconditional import-time
# requirement for `import pykmp`. Import `PySerialClientCommunicator` like this:
# `from pykmp.client import PySerialClientCommunicator`.
__all__ = [
    "PYSERIAL_AVAILABLE",
    "REGISTERS",
    "UNITS_NAMES",
    "ClientCommunicator",
    "FloatCodec",
    "GetRegisterRequest",
    "GetRegisterResponse",
    "GetSerialRequest",
    "GetSerialResponse",
    "GetTypeRequest",
    "GetTypeResponse",
    "RegisterData",
    "RegisterID",
]
