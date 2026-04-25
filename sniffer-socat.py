import fileinput
import pykmp

tx_buf = b''
rx_buf = b''

class Mode:
    NONE = 0
    READ = 1
    WRITE = 2
mode = Mode.NONE

client_codec = pykmp.client.ClientCodec()

def find_packet(buf, start_mark):
    start = buf.find(bytes([start_mark]))
    stop = buf.find(bytes([pykmp.constants.ByteCode.STOP.value]))
    if start == -1:
        return (None, buf)
    if stop == -1:
        return (None, buf)
    if start > 0:
        print(f'# !!! extra content before start-of-packet: {buf[0:start].hex()}')
        buf = buf[start:]
        stop = stop - start
        start = 0
    return (buf[start:stop + 1], buf[stop + 1:])

def handle_tx(buf):
    while True:
        packet, buf = find_packet(buf, pykmp.constants.ByteCode.START_TO_METER.value)
        if packet is None:
            break
        try:
            print(f'##> {packet.hex("-")} ({len(packet)} bytes)')
            parsed = client_codec.decode_command(packet)
            print(f'>>> {parsed}')
        except pykmp.client.UnknownCidError as e:
            print(f'>>> Unknown {e.cid:#02x}: {e.raw_data.hex(" ")}')
        except Exception as e:
            print(f'>>> {type(e)} {e}')
    return buf

def handle_rx(buf):
    while True:
        packet, buf = find_packet(buf, pykmp.constants.ByteCode.START_FROM_METER.value)
        if packet is None:
            break
        try:
            parsed = client_codec.decode_response(packet)
            print(f'##< {packet.hex("-")} ({len(packet)} bytes)')
            print(f'<<< {parsed}')
            if regs := getattr(parsed, 'registers', None):
                for (num, reg) in regs.items():
                    name = pykmp.constants.REGISTERS.get(num, f"R-{num}")
                    output = pykmp.registers.RegisterOutput.from_register_data(reg)
                    print(f'  | {output.to_pretty_line()}')
            if register_ids := getattr(parsed, 'register_ids', None):
                for rid in register_ids:
                    print(f' {rid:>4} | {pykmp.constants.REGISTERS.get(rid, "<unknown>")}')
            if log := getattr(parsed, 'log', None):
                for i, row in enumerate(log):
                    for reg in row:
                        output = pykmp.registers.RegisterOutput.from_register_data(reg)
                        print(f'{i:>2} | {output.to_pretty_line()}')
        except pykmp.client.UnknownCidError as e:
            print(f'<<< Unknown {e.cid:#02x}: {e.raw_data.hex(" ")}')
            if e.cid == 0xb8:
                print(f'  | len: {len(e.raw_data)}')
        except Exception as e:
            print(f'<<< {type(e)} {e}')
    return buf

for line in fileinput.input():
    if len(line.strip()) == 0:
        pass
    elif line.startswith('> '):
        mode = Mode.WRITE
    elif line.startswith('< '):
        mode = Mode.READ
    elif line.startswith(' '):
        match mode:
            case Mode.READ:
                rx_buf += bytes.fromhex(line)
                rx_buf = handle_rx(rx_buf)
            case Mode.WRITE:
                tx_buf += bytes.fromhex(line)
                tx_buf = handle_tx(tx_buf)
            case _:
                print (f'# !!! unknown mode when handling {line=}')
    else:
        print(f'# {line=}')

if count := len(tx_buf):
    print(f'!!! unparsed TX data ({count} bytes)')
if count := len(rx_buf):
    print(f'!!! unparsed RX data ({count} bytes)')
