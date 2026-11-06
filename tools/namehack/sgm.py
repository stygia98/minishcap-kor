# VBA 세이브스테이트(.sgm, gzip) → EWRAM/VRAM/OAM/팔레트 추출 (롬 데이터로 위치 역산)
import gzip, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx import K, group
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load(path):
    d = gzip.open(path).read()
    g5 = group(5)
    obj = next(e for e in g5 if e["dest"] == 0x6014800)
    v = d.find(K[obj["src"]:obj["src"] + 0x100]) - 0x14800          # VRAM 기준
    hira = d.find(K[0x8FA700 - 0x8000000 + 0xC0: 0x8FA700 - 0x8000000 + 0x200])
    ew = hira - 0x1A40 - 0xC0 if hira >= 0 else -1                      # EWRAM 기준(키보드 타일맵)
    return d, v, ew

if __name__ == "__main__":
    d, v, ew = load(sys.argv[1])
    print("크기", len(d), "VRAM@", hex(v), "EWRAM@", hex(ew))
