# 번역 진실원본 생성: J롬 일본어 + K롬 현재 한국어를 메시지 단위로 정렬 -> work/script.json
# 스키마: {"base":"0xE60000","blocks":[{"n":1,"msgs":[{"jp":..,"kr":<현재한글>,"ko":""}]}]}
#   jp = 일본어 원문(참고), kr = 현재 K롬 한글(참고/수정대상), ko = 새 번역(빈값이면 현재 kr 유지)
import os, sys, struct, zipfile, json
sys.path.insert(0, os.path.dirname(__file__))
import mc_codec as mc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JZIP = os.path.join(ROOT, "script-japan", "rom_script_cut(j).zip")
JTBL = os.path.join(ROOT, "script-japan", "jp-table.tbl")
KTBL = os.path.join(ROOT, "script-kor", "kor-table.tbl")
KROM = os.path.join(ROOT, "roms", "The Legend of Zelda - Fushigi no Boushi(K)_base.gba")
KCUT = os.path.join(ROOT, "script-kor", "rom_script_cut(k).zip")
BASE = 0xE60000
J_LAST_END = 0x1234   # 블록80 실제 끝(파일 안 오프셋)
OUT  = os.path.join(ROOT, "work", "script.json")

def k_blocks(kr):
    """K롬 대사 디렉토리(0xE60000, 80엔트리) -> [block bytes x80]. 마지막 블록 끝은 cut(k) 파일 길이로 보정."""
    # 블록80(index79): 끝 오프셋이 디렉토리에 없음 -> cut(k) 80.gba 길이 사용
    with zipfile.ZipFile(KCUT) as z:
        last_len = len(z.read("80.gba"))
    return mc.k_split(kr, BASE, last_len)

def main():
    j1, j2, j3, jl, _ = mc.load_tbl(JTBL)
    k1, k2, k3, kl, _ = mc.load_tbl(KTBL)
    kr = open(KROM, "rb").read()
    kblocks = k_blocks(kr)
    with zipfile.ZipFile(JZIP) as z:
        jblocks = [z.read("%d.gba" % bn) for bn in range(1, 81)]
    # cut(j) 80.gba는 대사 영역 끝(J 0x9DD6F0 = 파일 0x1234)보다 856바이트 더 잘려 있음
    # (뒤는 스프라이트 위치표 gExtraFrameOffsets, tmc assets.json: JP 대사 0x9B1A30+0x2BCC0) → 대사 끝에서 자름
    jblocks[79] = jblocks[79][:J_LAST_END]

    out, specials, tot = [], [], 0
    for bn in range(1, 81):
        _, jmsgs = mc.parse_block(jblocks[bn-1])
        _, kmsgs = mc.parse_block(kblocks[bn-1])
        # J를 척추로 정렬(J는 항상 정상 파싱). 메시지 수가 다르면 K가 비표준 -> special 로 표시하고
        # 삽입 시 원본 K 블록 바이트를 통째로 보존(건드리지 않음).
        special = len(jmsgs) != len(kmsgs)
        if special:
            specials.append(bn)
        n = len(jmsgs)
        msgs = []
        for i in range(n):
            jp = mc.decode(jmsgs[i], j1, j2, j3, jl)
            kc = "" if special else (mc.decode(kmsgs[i], k1, k2, k3, kl) if i < len(kmsgs) else "")
            msgs.append({"jp": jp, "kr": kc, "ko": ""})
        tot += n
        blk = {"n": bn, "msgs": msgs}
        if special:
            blk["special"] = True   # 원본 K 보존(삽입기에서 통째로 복사)
        out.append(blk)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"base": "0x%X" % BASE, "blocks": out}, f, ensure_ascii=False, indent=0)
    print("완료: 80블록 %d메시지 -> work/script.json (special 블록: %s)" % (tot, specials or "없음"))

if __name__ == "__main__":
    main()
