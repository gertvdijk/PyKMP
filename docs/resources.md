# KMP protocol documentation
<!--
SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>

SPDX-License-Identifier: CC0-1.0
-->

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

[multical-hu-kmp-modbus-datasheet]: https://www.multical.hu/upload/files/Modbus_KMP_TCP_IP.pdf
[meterlogger-wiki-kmp]: https://github.com/nabovarme/MeterLogger/wiki/Kamstrup-Protocol
