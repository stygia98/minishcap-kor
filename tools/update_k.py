# [③] work/script.json 의 ko → resource/script-kor/rom_script_cut(k1.1).zip 갱신
#   python tools/update_k.py
#   검사: ko 인코딩(실패 시 중단) · 제어 토큰 jp 비교(경고) · 블록8 지명 폰트 글자(경고)
#   ko 가 빈 메시지는 원본 k0.3 바이트 그대로
#   zip 형식(k0.3과 같음): 0 = 마스터(80개 시작 주소) / 1~80 = 블록 시작~마지막 <END> / K = 마스터+블록(각 16바이트 FF 정렬)
import os, sys, json, re, struct, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mc_codec as mc
import rom_stage

R = rom_stage.ROOT
SRC = os.path.join(R, "work", "script.json")
KTBL = os.path.join(R, "resource", "script-kor", "kor-table.tbl")
ATBL = os.path.join(R, "resource", "script-kor", "kor-area.tbl")
K03 = os.path.join(R, "resource", "script-kor", "rom_script_cut(k0.3).zip")
K10 = os.path.join(R, "resource", "script-kor", "rom_script_cut(k1.1).zip")

# 원시 {0B..}~{0F..} 는 J 폰트 글자(B버튼 아이콘 등)라 제어 비교에서 제외
TOK = re.compile(r"<[^<>]+>|\{(?!0[B-Fb-f])[0-9A-Fa-f]{2,6}\}")

def ctrl_tokens(s):
    """제어 토큰(<...>, {..})만 순서대로. <BR>은 줄바꿈이라 비교에서 제외(번역이 바꿀 수 있음)."""
    if "<END>" in s:  # 첫 <END> 뒤는 블록 정렬 패딩 → 비교 제외
        s = s[:s.index("<END>") + len("<END>")]
    return [t for t in TOK.findall(s) if t != "<BR>"]

def area_chars():
    """kor-area.tbl -> 글리프 순서 글자 목록(인덱스 = 지명 폰트 글리프 번호)"""
    out = []
    for line in open(ATBL, encoding="cp949").read().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            assert int(k[4:], 16) == len(out), "kor-area.tbl 순서 오류: " + line
            out.append(v)
    return out

def pack(blocks):
    """블록 80개 → (마스터, 전체). 블록마다 16바이트 FF 정렬"""
    off, nd = 80 * 4, []
    for b in blocks:
        nd.append(off); off += len(b) + (-len(b) % 16)
    master = b"".join(struct.pack("<I", d) for d in nd)
    return master, master + b"".join(b + b"\xFF" * (-len(b) % 16) for b in blocks)

def main():
    enc = mc.load_tbl(KTBL)[4]
    area = set(area_chars())
    data = json.load(open(SRC, encoding="utf-8"))
    z3 = zipfile.ZipFile(K03)
    blocks, warns, fails, changed = [], [], [], 0
    for blk in data["blocks"]:
        n = blk["n"]
        orig = mc.parse_block(z3.read(str(n)))[1]
        assert len(orig) == len(blk["msgs"]), "블록%d 메시지 수가 k0.3과 다름" % n
        msgs = []
        for i, m in enumerate(blk["msgs"]):
            ko = m.get("ko", "").replace("\r", "").replace("\n", "")   # 표시용 줄바꿈 제거(줄은 <BR>로만)
            if not ko.strip():
                msgs.append(orig[i]); continue
            if n == 8 and 11 <= i <= 40:                               # 지명은 지명 폰트 82글자 안에서만 표시
                bad = sorted(set(re.sub(r"<[^>]*>", "", ko.split("<END>")[0])) - area)
                if bad:
                    print("  ⚠ 블록8 #%d 지명 폰트에 없는 글자 %s" % (i, "".join(bad)))
            if ctrl_tokens(ko) != ctrl_tokens(m.get("jp") or ""):
                warns.append((n, i, ctrl_tokens(m.get("jp") or ""), ctrl_tokens(ko)))
            try:
                msgs.append(mc.encode(ko, enc)); changed += 1
            except ValueError as e:
                fails.append("블록%d #%d: %s" % (n, i, e))
        blk_bytes = mc.build_block(msgs)
        # 블록 끝 = 마지막 메시지 <END> (뒤 쓰레기 없이)
        cnt = len(msgs)
        last = struct.unpack_from("<I", blk_bytes, (cnt - 1) * 4)[0]
        blocks.append(blk_bytes[:mc.msg_end(blk_bytes + b"\x00", last)])
    if warns:
        print("  ⚠ 제어 토큰 불일치 %d건(번역 실수 가능 — 원본 제어코드 보존 필요):" % len(warns))
        for n, i, ref, ko in warns[:20]:
            print("    블록%d #%d: 원본%s != 번역%s" % (n, i, ref, ko))
        if len(warns) > 20:
            print("    ... 외 %d건" % (len(warns) - 20))
    if fails:
        print("\n".join("  인코딩 실패 " + f for f in fails))
        sys.exit("중단: 인코딩 실패 %d건 — script.json 수정 후 다시 실행(k1.1 zip은 그대로)" % len(fails))
    master, whole = pack(blocks)
    tmp = K10 + ".tmp"
    with zipfile.ZipFile(tmp, "w", z3.infolist()[0].compress_type) as z:
        z.writestr("0", master)
        for i, b in enumerate(blocks, 1):
            z.writestr(str(i), b)
        z.writestr("K", whole)
    os.replace(tmp, K10)
    print("k1.1 갱신: 번역 %d메시지, 대사 %d바이트 -> %s" % (changed, len(whole), K10))

if __name__ == "__main__":
    main()
