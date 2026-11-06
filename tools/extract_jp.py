# 1단계: 일본어 대사 추출 -> 단일 진실원본 work/script.json (+ 블록별 참고 txt)
# script.json: {"blocks":[{"n":1,"msgs":[{"jp":"<디코딩원문>","ko":""}, ...]}, ...]}
#   ko="" = 미번역. 삽입 시 ko 비면 원본 바이트 그대로 보존(일본어/한자 폰트 커버리지 걱정 X).
import os, sys, zipfile, json
sys.path.insert(0, os.path.dirname(__file__))
import mc_codec as mc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP  = os.path.join(ROOT, "script-japan", "rom_script_cut(j).zip")
TBL  = os.path.join(ROOT, "script-japan", "jp-table.tbl")
OUT  = os.path.join(ROOT, "work", "jp")

def header(bn, cnt):
    return (
        "# block %02d · %d msgs · minish_cap 한글화 워크스페이스\n" % (bn, cnt) +
        "# 규칙: 'J:' = 일본어 원문(수정 금지, 참고용). 'K:' 줄만 번역으로 수정.\n"
        "#       줄바꿈=<BR>, 색/제어 태그(<green> 등)·원시코드({0309} 등)는 그대로 유지.\n"
        "#       빈/제어전용 메시지는 K를 건드리지 말 것(원문 그대로 왕복됨).\n\n"
    )

def main():
    one, two, three, leads, _ = mc.load_tbl(TBL)
    os.makedirs(OUT, exist_ok=True)
    blocks = []
    total_msgs = 0
    with zipfile.ZipFile(ZIP) as z:
        for bn in range(1, 81):
            data = z.read("%d.gba" % bn)
            _, msgs = mc.parse_block(data)
            total_msgs += len(msgs)
            decoded = [mc.decode(m, one, two, three, leads) for m in msgs]
            blocks.append({"n": bn, "msgs": [{"jp": t, "ko": ""} for t in decoded]})
            lines = [header(bn, len(msgs))]
            for idx, t in enumerate(decoded):
                lines.append("#%d\nJ: %s\nK: %s\n\n" % (idx, t, t))
            with open(os.path.join(OUT, "%02d.txt" % bn), "w", encoding="utf-8") as f:
                f.write("".join(lines))
    with open(os.path.join(ROOT, "work", "script.json"), "w", encoding="utf-8") as f:
        json.dump({"blocks": blocks}, f, ensure_ascii=False, indent=0)
    print("추출 완료: 80개 블록, 총 %d개 메시지 -> work/script.json" % total_msgs)

if __name__ == "__main__":
    main()
