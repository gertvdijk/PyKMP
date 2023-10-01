# Connecting over the network (ser2net)
<!--
SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>

SPDX-License-Identifier: CC0-1.0
-->

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
A connection can be made from any other host using the
[`socket://` URL handler with PySerial][pyserial-url-handlers-socket] like this:

```console
$ pykmp-tool {==--serial-device socket://hostname:2002==} [...]
```

Or use the environment variable to not having to specify it in every command:

```console
$ export PYKMP_SERIAL_DEVICE=socket://hostname:2002
```

[ser2net-github]: https://github.com/cminyard/ser2net
[pyserial-url-handlers-socket]: https://pyserial.readthedocs.io/en/latest/url_handlers.html#socket
