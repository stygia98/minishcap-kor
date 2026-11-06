# work/script.json 번역 + 이름입력 한글개조 + K롬 버그픽스를 한 번에 roms/...(K).gba 로 덤프.
#   기준(원본, 보존): roms/...(K)_base.gba   ← 절대 수정 안 함(덤프 기준)
#   출력(최종, 플레이): roms/...(K).gba       ← 매번 새로 생성(번역+개조+버그픽스)
#   중간파일(_edit/_name) 안 남김(임시폴더 사용 후 삭제).
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "namehack"))
import insert_kr
import patches
import rcaption
import build_namehack as bnh

FINAL = os.path.join(ROOT, "roms", "The Legend of Zelda - Fushigi no Boushi(K).gba")
tmp = os.path.join(tempfile.gettempdir(), "mc_dump_edit.gba")
def check_area_names():
    """블록8 지명(ko)은 지명 폰트 82글자(kor-area.tbl) 안에서만 표시됨 → 없는 글자 경고(엉뚱한 글리프로 나옴)"""
    import json, re
    ok = set(patches.area_chars())
    s = json.load(open(os.path.join(ROOT, "work", "script.json"), encoding="utf-8"))
    for b in s["blocks"]:
        if b["n"] != 8:
            continue
        for i, m in enumerate(b["msgs"]):
            if not 11 <= i <= 40:          # #11~40만 지명(#1~4 등은 일반 대사)
                continue
            t = re.sub(r"<[^>]*>", "", m["ko"].split("<start>")[0])
            bad = sorted(set(t) - ok)
            if bad:
                print("  ⚠ 블록8 #%d 지명 폰트에 없는 글자 %s: %s" % (i, "".join(bad), t))

try:
    check_area_names()
    print("[1/3] 번역 덤프 (script.json → 임시)")
    insert_kr.main(tmp)
    print("[2/3] 이름입력 한글 조합형 개조")
    bnh.main(tmp, FINAL)
    print("[3/3] K롬 버그픽스")
    rom = bytearray(open(FINAL, "rb").read())
    patches.apply(rom)
    rcaption.apply(rom)          # R버튼 동작 캡션(일본어판 기준 번역) 그래픽
    open(FINAL, "wb").write(rom)
    print("완료:", FINAL)
    # 검수 앱도 현재 script.json(블록 검수 체크 포함)으로 다시 생성
    import gen_review
    gen_review.main()
finally:
    if os.path.exists(tmp):
        os.remove(tmp)
