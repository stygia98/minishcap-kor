# K/J롬 Thumb 디스어셈블: python thumbdis.py [K|J] 주소 바이트수
import os, sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROMS = {"K": "The Legend of Zelda - Fushigi no Boushi(K)_base.gba", "J": "1743 - The Legend of Zelda - Fushigi no Boushi(J).gba",
        "U": "1865 - Legend of Zelda, The - The Minish Cap (U).gba", "E": "The Legend of Zelda - Fushigi no Boushi(K)_edit.gba"}
def rom(k): return open(os.path.join(ROOT, "roms", ROMS[k]), "rb").read()
def dis(k, addr, n):
    d = rom(k); o = addr - 0x08000000
    for i in Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(d[o:o + n], addr):
        print("%08x  %-10s %s %s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
if __name__ == "__main__":
    dis(sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3]))
