# API reference documentation – codec module
<!--
SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>

SPDX-License-Identifier: CC0-1.0
-->

::: pykmp.codec
    options:
        members: []
        show_root_heading: false
        show_root_toc_entry: true

## Concrete classes

::: pykmp.codec.PhysicalCodec
::: pykmp.codec.DataLinkCodec
::: pykmp.codec.ApplicationCodec
::: pykmp.codec.FloatCodec

## Data classes & types

::: pykmp.codec.PhysicalBytes
::: pykmp.codec.DataLinkBytes
::: pykmp.codec.ApplicationBytes
::: pykmp.codec.ApplicationDataBytes
::: pykmp.codec.ApplicationData
::: pykmp.codec.DataLinkData
::: pykmp.codec.PhysicalDirection

## Exceptions

::: pykmp.codec.AckReceivedException
::: pykmp.codec.BaseCodecError
::: pykmp.codec.OutOfRangeError
::: pykmp.codec.DataLengthUnexpectedError
::: pykmp.codec.BoundaryByteInvalidError
::: pykmp.codec.InvalidDestinationAddressError
::: pykmp.codec.UnsupportedDecimalExponentError
::: pykmp.codec.CrcChecksumInvalidError
