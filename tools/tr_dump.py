# 번역 작업용 블록 덤프: 번역 대상 메시지를 [화자] 일본어 / 현재한글(참고) 로 출력
#   사용: python tools/tr_dump.py 12 [13 ...]   (--all 이면 이미 번역된 것도 출력)
import os, sys, json, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main(args):
    show_all = "--all" in args
    nums = [int(a) for a in args if a.isdigit()]
    s = json.load(open(os.path.join(ROOT, "work", "script.json"), encoding="utf-8"))
    spk_path = os.path.join(ROOT, "work", "speakers.json")
    spk = json.load(open(spk_path, encoding="utf-8")) if os.path.exists(spk_path) else {}
    for b in s["blocks"]:
        if b["n"] not in nums:
            continue
        for i, m in enumerate(b["msgs"]):
            if not re.sub(r"<[^>]*>|\{[^}]*\}", "", m["jp"]).strip():
                continue
            if m["ko"] and not show_all:
                continue
            who = ",".join(spk.get("%d#%d" % (b["n"], i), []))
            print("%d#%d [%s]\n  J %s\n  K %s" % (b["n"], i, who, m["jp"], m["kr"]))

if __name__ == "__main__":
    main(sys.argv[1:])
