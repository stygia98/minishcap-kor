# 왕복 무결성 검증: J(cut zip)·K(최종 (K)_ver1.1.gba) 전 메시지 decode -> encode == 원본 바이트?
import os, sys, zipfile
sys.path.insert(0, os.path.dirname(__file__))
import mc_codec as mc
import rom_stage

R = rom_stage.ROOT
JZIP = os.path.join(R, "resource", "script-japan", "rom_script_cut(j).zip")
JTBL = os.path.join(R, "resource", "script-japan", "jp-table.tbl")
KTBL = os.path.join(R, "resource", "script-kor", "kor-table.tbl")

def check(label, blocks, tbl):
    one, two, three, leads, enc = mc.load_tbl(tbl)
    bad = total = 0
    for bn, blk in enumerate(blocks, 1):
        for i, m in enumerate(mc.parse_block(blk)[1]):
            total += 1
            t = mc.decode(m, one, two, three, leads)
            try:
                e = mc.encode(t, enc)
                # J 테이블은 같은 글자가 코드 2개인 경우가 있어 문자열 기준 비교(J는 참고용, 재인코딩 안 함)
                ok = e == m if label == "K" else mc.decode(e, one, two, three, leads) == t
            except ValueError as e:
                ok = False; t += "  (%s)" % e
            if not ok:
                bad += 1
                if bad <= 10:
                    print("  %s 블록%d #%d 불일치: %s" % (label, bn, i, t[:80]))
    print("=== %s: %d메시지 중 불일치 %d ===" % (label, total, bad))
    return bad

def main():
    with zipfile.ZipFile(JZIP) as z:
        jblocks = [z.read(str(bn)) for bn in range(1, 81)]
    kblocks = mc.k_split(rom_stage.read_final(), 0xE60000, dir_fix=False)   # 최종 (K)_ver1.1.gba 대사(덤프 결과)
    bad = check("J", jblocks, JTBL) + check("K", kblocks, KTBL)
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
