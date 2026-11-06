# 3단계: work/script.json 의 번역을 K롬에 삽입(덤프)
# 규칙: 블록별로 메시지 재조립. ko 비었으면 원본 K 바이트 보존, special 블록은 통째 보존.
#       마스터 디렉토리(0xE60000, 80엔트리, BASE 상대 오프셋) 재계산. 원본 footprint 안에 들어가면 안전,
#       넘치면 뒤쪽 0xFF 패딩 여유분까지 사용(그래도 넘치면 중단 -> 재배치 필요).
import os, sys, json, struct, zipfile, re
sys.path.insert(0, os.path.dirname(__file__))
import mc_codec as mc

# 원시 {0B..}~{0F..} 는 J 폰트 글자(B버튼 아이콘 등)라 제어 비교에서 제외
TOK = re.compile(r"<[^<>]+>|\{(?!0[B-Fb-f])[0-9A-Fa-f]{2,6}\}")

def ctrl_tokens(s):
    """제어 토큰(<...>, {..})만 순서대로. <BR>은 줄바꿈이라 비교에서 제외(번역이 바꿀 수 있음)."""
    if "<start>" in s:  # 첫 <start> 뒤는 블록 정렬 패딩(00…+FF…) → 비교 제외
        s = s[:s.index("<start>") + len("<start>")]
    return [t for t in TOK.findall(s) if t != "<BR>"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "work", "script.json")
KTBL = os.path.join(ROOT, "script-kor", "kor-table.tbl")
KROM = os.path.join(ROOT, "roms", "The Legend of Zelda - Fushigi no Boushi(K)_base.gba")
KCUT = os.path.join(ROOT, "script-kor", "rom_script_cut(k).zip")
DEFAULT_OUT = os.path.join(ROOT, "roms", "The Legend of Zelda - Fushigi no Boushi(K)_edit.gba")

def last_block_len():
    with zipfile.ZipFile(KCUT) as z:
        return len(z.read("80.gba"))

def main(out_path):
    data = json.load(open(SRC, encoding="utf-8"))
    base = int(data["base"], 16)
    _, _, _, _, enc = mc.load_tbl(KTBL)
    kr = open(KROM, "rb").read()
    last_len = last_block_len()
    orig_total = struct.unpack_from("<I", kr, base + 79*4)[0] + last_len
    # 원본 K 블록 바이트(80개, 블록76 디렉토리 오류 보정 포함)
    korig = mc.k_split(kr, base, last_len)

    new_blocks = []
    changed = 0
    warns = []
    for blk in data["blocks"]:
        bn = blk["n"]
        ob = korig[bn-1]
        if blk.get("special"):
            new_blocks.append(ob)
            continue
        _, omsgs = mc.parse_block(ob)
        msgs = []
        for i, m in enumerate(blk["msgs"]):
            ko = m.get("ko", "").replace("\r", "").replace("\n", "")  # 표시용 줄바꿈 제거(줄은 <BR>로만)
            if ko.strip():
                # 안전장치: 제어 토큰(명령+인자 통째)이 일본어 원문과 다르면 경고
                # (현재 한글은 제어코드 파손이 있어 기준으로 부적합 — ctrl_census.py 참고)
                ref = m.get("jp") or ""
                if ctrl_tokens(ko) != ctrl_tokens(ref):
                    warns.append((bn, i, ctrl_tokens(ref), ctrl_tokens(ko)))
                try:
                    msgs.append(mc.encode(ko, enc))
                    changed += 1
                except Exception as e:
                    print("  인코딩 실패 블록%d #%d: %s" % (bn, i, e))
                    msgs.append(omsgs[i])   # 실패 시 원본 유지
            else:
                msgs.append(omsgs[i] if i < len(omsgs) else b"")
        nb = mc.build_block(msgs)
        # 원본처럼 블록을 16바이트 경계로 FF 패딩(GBA ldr은 정렬 필수 — 어긋나면 포인터 테이블이 깨짐)
        new_blocks.append(nb + b"\xFF" * (-len(nb) % 16))

    # 영역 재조립: [80엔트리 디렉토리][블록들]
    head = 80 * 4
    off = head
    diro = []
    for b in new_blocks:
        diro.append(off); off += len(b)
    new_total = off
    region = bytearray()
    for d in diro:
        region += struct.pack("<I", d)
    for b in new_blocks:
        region += b
    assert len(region) == new_total

    # 용량 검사: 원본 footprint + 뒤쪽 0xFF 패딩 여유
    free_end = base + orig_total
    while free_end < len(kr) and kr[free_end] == 0xFF:
        free_end += 1
    capacity = free_end - base
    print("원본 영역=%d, 새 영역=%d, 여유포함 용량=%d" % (orig_total, new_total, capacity))
    if new_total > capacity:
        sys.exit("중단: 용량 초과(%d > %d). 스크립트 재배치 필요." % (new_total, capacity))

    out = bytearray(kr)
    out[base: base + new_total] = region
    if new_total < orig_total:   # 줄어든 부분은 0xFF로 청소
        out[base + new_total: base + orig_total] = b"\xFF" * (orig_total - new_total)

    with open(out_path, "wb") as f:
        f.write(out)
    diff = sum(1 for i in range(len(kr)) if out[i] != kr[i])
    print("덤프 완료: %s" % out_path)
    print("  교체 메시지 %d개, 원본 대비 바이트 차이 %d" % (changed, diff))
    if warns:
        print("  ⚠ 제어 토큰 불일치 %d건(번역 실수 가능 — 원본 제어코드 보존 필요):" % len(warns))
        for bn, i, ref, ko in warns[:20]:
            print("    블록%d #%d: 원본%s != 번역%s" % (bn, i, ref, ko))
        if len(warns) > 20:
            print("    ... 외 %d건" % (len(warns) - 20))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT)
