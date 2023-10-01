# Battery consumption 🪫
<!--
SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>

SPDX-License-Identifier: CC0-1.0
-->

Most Kamstrup meters for heat are battery-powered.
Using the optical/infrared interface will draw extra power from the battery and it may
deplete sooner when using this on a regular basis.

Extending the interval of reading should help, as well as requesting all data you need
in a single request – avoid looping with just a single register ID for example.

Reading the battery level is not (yet) possible.

IR-circuit may only be activated with a magnet in the optical head.
In addition to that, some (older) models may require periodic re-activation of the
IR-circuit by pressing any button on the panel.
