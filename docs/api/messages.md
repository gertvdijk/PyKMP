# API reference documentation – messages module
<!--
SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>

SPDX-License-Identifier: CC0-1.0
-->

::: pykmp.messages
    options:
        members: []
        show_root_heading: false
        show_root_toc_entry: true

## Concrete message types

::: pykmp.messages.GetTypeRequest
::: pykmp.messages.GetTypeResponse
::: pykmp.messages.GetSerialRequest
::: pykmp.messages.GetSerialResponse
::: pykmp.messages.GetRegisterRequest
::: pykmp.messages.GetRegisterResponse

## Data classes & types

::: pykmp.messages.RegisterData
::: pykmp.messages.RegisterID
::: pykmp.messages.RegisterUnit
::: pykmp.messages.RegisterValueBytes
::: pykmp.messages.Req_t_co
::: pykmp.messages.Res_t_co

## Base classes

::: pykmp.messages.HasCommandIdAndName
::: pykmp.messages.BaseRequest
::: pykmp.messages.BaseResponse
::: pykmp.messages.SupportsDecode
::: pykmp.messages.SupportsEncode
::: pykmp.messages.WithDataMixin

## Exceptions

::: pykmp.messages.MessageCidMismatchError
::: pykmp.messages.DataWithNoDataError
::: pykmp.messages.SoftwareRevisionInvalidError
::: pykmp.messages.SerialNumberInvalidError
