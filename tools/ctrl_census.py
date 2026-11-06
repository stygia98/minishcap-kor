# 제어코드 전수 조사: 메시지별로 일본어 원문(jp)과 대상 필드(kr/ko)의 제어 토큰 순서 비교
#   사용: python tools/ctrl_census.py [kr|ko]   -> work/ctrl_census_<필드>.txt
#   <BR>은 번역 시 조정 대상이라 비교 제외. 블록 끝 쓰레기 데이터(JUNK)와 special/블록8 제외.
import os, sys, json, re, difflib
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 원시 {0B..}~{0F..} 는 J 폰트 글자(B버튼 아이콘 등)라 제어 비교에서 제외
TOK = re.compile(r"<[^<>]+>|\{(?!0[B-Fb-f])[0-9A-Fa-f]{2,6}\}")
JUNK = {(75, 39), (80, 101)}   # 대사가 아닌 블록 끝 바이너리(ホホホ… 반복)

def ctrl(t):
    # 첫 <start> 뒤는 블록 정렬용 패딩(00…+FF…, 표 디코딩 시 ホホホ로 보임) → 본문만 비교
    if "<start>" in t:
        t = t[:t.index("<start>") + len("<start>")]
    return [x for x in TOK.findall(t) if x != "<BR>"]

def kind(x):
    return re.sub(r":.*>", ">", x) if x.startswith("<") else "{raw}"

def main(field):
    s = json.load(open(os.path.join(ROOT, "work", "script.json"), encoding="utf-8"))
    cj, cf, out, nmis = Counter(), Counter(), [], 0
    for b in s["blocks"]:
        if b.get("special") or b["n"] == 8:
            continue
        for i, m in enumerate(b["msgs"]):
            if (b["n"], i) in JUNK or not m.get(field):
                continue
            j, f = ctrl(m["jp"]), ctrl(m[field])
            cj.update(map(kind, j)); cf.update(map(kind, f))
            if j != f:
                nmis += 1
                out.append("블록%d #%d" % (b["n"], i))
                for tag, a1, a2, b1, b2 in difflib.SequenceMatcher(None, j, f).get_opcodes():
                    if tag != "equal":
                        out.append("   %-7s jp[%s] -> %s[%s]" % (tag, " ".join(j[a1:a2]), field, " ".join(f[b1:b2])))
    head = ["제어코드 전수 조사: jp vs %s" % field, "종류        jp     %s" % field]
    head += ["  %-10s %5d %5d" % (k, cj[k], cf[k]) for k in sorted(set(cj) | set(cf))]
    head += ["불일치 메시지: %d" % nmis, ""]
    path = os.path.join(ROOT, "work", "ctrl_census_%s.txt" % field)
    open(path, "w", encoding="utf-8").write("\n".join(head + out) + "\n")
    print("\n".join(head)); print("-> %s" % path)
    return nmis

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "kr")
