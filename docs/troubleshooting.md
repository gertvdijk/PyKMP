# Troubleshooting
<!--
SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>

SPDX-License-Identifier: CC0-1.0
-->

## Unable to run the tool `pykmp-tool: command not found`

Using a Python package manager (e.g. pip) should ensure the entry point should be
installed somewhere in a directory that's on your PATH, but apparently that failed.

As an alternative, you can try to substitute `pykmp-tool` with `python -m pykmp.tool`.

## Unable to get a reading (connection timeout)

- Make sure your IR head has an included magnet that activates the meter's IR circuit.
  If in doubt, activate it by pressing any button and try to get a reading while the
  display is active.
- Make sure the RX/TX is aligned with the meter.
  It's most if not all cases the IR head has to be placed in *upside-down position*.
- Try to re-align around the position of the IR optical head while keeping a command
  running in a loop in your shell.
