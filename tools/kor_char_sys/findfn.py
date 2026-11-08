# U롬(tmc 디컴파일 주소 기준) 함수 → J/K롬 동일 함수 주소 찾기 (BL 오프셋 마스킹 패턴 검색)
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(ROOT, "resource", "roms")
U = open(os.path.join(R, "1865 - Legend of Zelda, The - The Minish Cap (U).gba"), "rb").read()
K = open(os.path.join(R, "The Legend of Zelda - Fushigi no Boushi(K)_ver1.1.gba"), "rb").read()

def pattern(addr, n=40):
    o = addr - 0x08000000
    b = U[o:o + n]
    pat = b""
    i = 0
    while i < len(b):
        hw = b[i] | b[i+1] << 8
        if hw & 0xF800 == 0xF000 and i + 3 < len(b):      # BL 쌍: 오프셋 무시
            pat += b"[\x00-\xff]{3}" + re.escape(bytes([b[i+3]]))[:0] + b"[\xf8-\xff]"
            i += 4; continue
        if hw & 0xF800 == 0x4800:                          # ldr rX,[pc,#] : 오프셋 무시
            pat += b"[\x00-\xff]" + re.escape(bytes([b[i+1]]))
            i += 2; continue
        pat += re.escape(b[i:i+2]); i += 2
    return re.compile(pat, re.S)

def find(addr, n=40):
    hits = [m.start() for m in pattern(addr, n).finditer(K) if m.start() % 2 == 0]
    return [0x08000000 + h for h in hits]

if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(a, [hex(h) for h in find(int(a, 16))])
