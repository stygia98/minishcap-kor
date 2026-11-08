# J 원본 롬 ↔ 최종 K 롬(dump.py 결과) 차이를 패치 데이터로 저장 -> patch_data.py (패처 exe에 내장)
#   형식(zlib 압축 전): 'MCKP' + [오프셋 u32 · 길이 u32 · 바이트]* (차이 구간, 8바이트 이하 틈은 합침)
#   사용: python tools/rompatcher/make_patch.py   (덤프 후 실행 → exe 다시 빌드)
import os, glob, struct, zlib, base64

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
J = glob.glob(os.path.join(ROOT, "resource", "roms", "*(J).gba"))[0]
K = os.path.join(ROOT, "resource", "roms", "The Legend of Zelda - Fushigi no Boushi(K)_ver1.1.gba")
GAP = 8

def runs(a, b):
    i, n = 0, len(b)
    while i < n:
        if i < len(a) and a[i] == b[i]:
            i += 1
            continue
        s = e = i
        while e < n:
            if e < len(a) and a[e] == b[e]:
                k = e
                while k < n and k < len(a) and a[k] == b[k] and k - e <= GAP:
                    k += 1
                if k - e > GAP or k >= n:
                    break
                e = k
            else:
                e += 1
        yield s, b[s:e]
        i = e

def main():
    j, k = open(J, "rb").read(), open(K, "rb").read()
    body = bytearray(b"MCKP")
    cnt = 0
    for off, data in runs(j, k):
        body += struct.pack("<II", off, len(data)) + data
        cnt += 1
    comp = zlib.compress(bytes(body), 9)
    # 자체 검증: J + 패치 == K
    out = bytearray(j[:len(k)].ljust(len(k), b"\0"))
    p = 4
    while p < len(body):
        off, ln = struct.unpack_from("<II", body, p); p += 8
        out[off:off + ln] = body[p:p + ln]; p += ln
    assert bytes(out) == k, "패치 자체 검증 실패"
    with open(os.path.join(HERE, "patch_data.py"), "w", encoding="utf-8") as f:
        f.write("# 자동 생성(make_patch.py) — 수정 금지\n")
        f.write("J_SIZE = %d\nJ_CRC = 0x%08X\nK_SIZE = %d\nK_CRC = 0x%08X\n" % (len(j), zlib.crc32(j), len(k), zlib.crc32(k)))
        f.write("DATA = (\n")
        s = base64.b64encode(comp).decode()
        for i in range(0, len(s), 120):
            f.write('    "%s"\n' % s[i:i + 120])
        f.write(")\n")
    print("구간 %d개, 원본 %d바이트 → 압축 %d바이트" % (cnt, len(body), len(comp)))
    print("J CRC %08X → K CRC %08X" % (zlib.crc32(j), zlib.crc32(k)))

if __name__ == "__main__":
    main()
