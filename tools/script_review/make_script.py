# [①] work/script.json + work/review.html 생성: 대사 zip 3개를 디코딩해 메시지별 jp / kr / ko 를 각각 채움
#   jp = rom_script_cut(j).zip     일본판 원문          (jp-table.tbl)
#   kr = rom_script_cut(k0.3).zip  원본 K해킹 한글       (kor-table.tbl, 블록8 #11~40 지명은 + kor-area.tbl)
#   ko = rom_script_cut(k1.0).zip  재번역 최종본(덤프된 롬)
#   python tools/script_review/make_script.py    → work/script.json 덮어씀(기존 파일은 upload/backup/ 에 자동 백업)
# 주의: review.html 에서 고치고 update_k10.py 를 안 돌린 내용은 k1.0 zip에 없으므로 사라짐 → ③ 후에 실행
import os, sys, json, zipfile, shutil, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tools/ (mc_codec·rom_stage)
import mc_codec as mc
import rom_stage

R = rom_stage.ROOT
JZIP = os.path.join(R, "resource", "script-japan", "rom_script_cut(j).zip")
K03 = os.path.join(R, "resource", "script-kor", "rom_script_cut(k0.3).zip")
K10 = os.path.join(R, "resource", "script-kor", "rom_script_cut(k1.0).zip")
JTBL = os.path.join(R, "resource", "script-japan", "jp-table.tbl")
KTBL = os.path.join(R, "resource", "script-kor", "kor-table.tbl")
ATBL = os.path.join(R, "resource", "script-kor", "kor-area.tbl")
OUT = os.path.join(R, "work", "script.json")
BASE = 0xE60000

def build():
    J = mc.load_tbl(JTBL)[:4]
    K = mc.load_tbl(KTBL)[:4]
    A = mc.load_tbl(ATBL)
    KA = (K[0], K[1], {**K[2], **A[2]}, K[3] | A[3])     # 블록8 지명: 0F 4F xx = 지명 폰트 글자
    zj, z3, z1 = (zipfile.ZipFile(p) for p in (JZIP, K03, K10))
    blocks = []
    for n in range(1, 81):
        mj, m3, m1 = (mc.parse_block(z.read(str(n)))[1] for z in (zj, z3, z1))
        assert len(mj) == len(m3) == len(m1), "블록%d 메시지 수 다름: j%d k0.3 %d k1.0 %d" % (n, len(mj), len(m3), len(m1))
        msgs = []
        for i in range(len(mj)):
            kt = KA if n == 8 and 11 <= i <= 40 else K
            msgs.append({"jp": mc.decode(mj[i], *J), "kr": mc.decode(m3[i], *kt), "ko": mc.decode(m1[i], *kt)})
        blocks.append({"n": n, "msgs": msgs})
    return {"base": "0x%X" % BASE, "blocks": blocks}

def main():
    data = build()
    if os.path.exists(OUT):
        bak = os.path.join(R, "upload", "backup", "script.before_make_script_%s.json" % time.strftime("%Y%m%d_%H%M%S"))
        shutil.copy2(OUT, bak)
        print("기존 script.json 백업:", bak)
    with open(OUT, "w", encoding="utf-8") as f:            # review.html 내보내기와 같은 압축 JSON
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("완료: 80블록 %d메시지 -> %s" % (sum(len(b["msgs"]) for b in data["blocks"]), OUT))
    import gen_review                                        # 검수 앱도 새 script.json으로 다시 생성
    gen_review.main()

if __name__ == "__main__":
    main()
