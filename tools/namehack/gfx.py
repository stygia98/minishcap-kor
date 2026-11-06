# K롬 gfx 그룹 표(0x8100770) 해석 / 이름 입력 키보드 타일맵 확인
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mc_codec as mc
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
K = open(os.path.join(ROOT, "roms", "The Legend of Zelda - Fushigi no Boushi(K)_base.gba"), "rb").read()
GROUPS, GBASE = 0x100770, 0x5A2B20
def u32(a): return struct.unpack_from("<I", K, a)[0]

def group(n):
    p = u32(GROUPS + n * 4) - 0x08000000
    out = []
    while True:
        a, dest, size = u32(p), u32(p + 4), u32(p + 8)
        out.append(dict(at=p, src=GBASE + (a & 0xFFFFFF), ctrl=(a >> 24) & 0xF, dest=dest,
                        size=size & 0x7FFFFFFF, comp=size >> 31))
        if not a >> 31: break
        p += 12
    return out

if __name__ == "__main__":
    one = mc.load_tbl(os.path.join(ROOT, "script-japan", "jp-table.tbl"))[0]
    for n in map(int, sys.argv[1:]):
        for e in group(n):
            print(n, {k: (hex(v) if isinstance(v, int) else v) for k, v in e.items()})
            if e["dest"] == 0x2001a40 and not e["comp"]:
                tm = struct.unpack_from("<%dH" % (e["size"] // 2), K, e["src"])
                for r in range(e["size"] // 64):
                    row = tm[r * 32:(r + 1) * 32]
                    print("%2d " % r + "".join(one.get((t & 0x3FF) >> 1, "·") if t & 0x3FF and not (t & 1) else ("." if not t & 0x3FF else "_") for t in row))
