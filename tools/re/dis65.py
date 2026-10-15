"""Linear 65816 disassembly of a LoROM routine: dis65.py <rom> <bank:addr hex> [count] [m] [x]

Tracks REP/SEP for M/X, stops after `count` instructions or at the first RTS/RTL/RTI/JMP/BRA
when the next address is not a known branch target. Uses the snesrecomp decoder.
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'snesrecomp' / 'recompiler'))
import snes65816 as d  # noqa: E402

rom = open(sys.argv[1], 'rb').read()
d.set_rom_mapping('lorom')
bank, addr = (int(v, 16) for v in sys.argv[2].split(':'))
count = int(sys.argv[3]) if len(sys.argv) > 3 else 120
m = int(sys.argv[4]) if len(sys.argv) > 4 else 0
x = int(sys.argv[5]) if len(sys.argv) > 5 else 0
targets = set()
pc = addr
for _ in range(count):
    off = d.lorom_offset(bank, pc)
    insn = d.decode_insn(rom, off, pc, bank, m, x)
    if insn is None:
        print(f'{bank:02X}:{pc:04X}  {rom[off]:02X}        ???')
        break
    raw = ' '.join(f'{b:02X}' for b in rom[off:off + insn.length])
    mode = insn.mode
    op = insn.operand
    if insn.mnem in ('REP', 'SEP'):
        if op & 0x20: m = 0 if insn.mnem == 'REP' else 1
        if op & 0x10: x = 0 if insn.mnem == 'REP' else 1
    name = getattr(mode, 'name', str(mode))
    width = {1: 2, 2: 2, 3: 4, 4: 6}.get(insn.length, 4)
    text = f'${op:0{width}X}' if insn.length > 1 else ''
    if insn.mnem.startswith('B') and insn.mnem not in ('BIT', 'BRK') or insn.mnem == 'BRL':
        targets.add(op)
    print(f'{bank:02X}:{pc:04X}  {raw:<12} {insn.mnem} {text:<8} [{name}] m{m}x{x}')
    pc = (pc + insn.length) & 0xFFFF
    if insn.mnem in ('RTS', 'RTL', 'RTI', 'JMP', 'JML', 'BRA', 'BRL') and pc not in targets:
        break
