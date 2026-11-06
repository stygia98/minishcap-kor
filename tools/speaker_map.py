# 화자 매핑: zeldaret/tmc 디컴파일(ref/tmc)에서 메시지 참조를 모아 (블록,메시지) -> 화자 후보 산출
#   TEXT_INDEX(category, index): category = 블록번호-1 (include/message.h enum 순서)
#   출처: data/scripts/**/*.inc 의 *Message* 명령, src/**/*.c 의 TEXT_INDEX(...)
#   이후 우리 대사의 <op07:XXYY>(이어지는 대사)·<select:XXYY>(선택지 분기)를 따라 화자 전파
#   사용: python tools/speaker_map.py  -> work/speakers.json + 커버리지 출력
import os, re, json, glob, struct
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMC = os.path.join(ROOT, "ref", "tmc")
SCRIPT = os.path.join(ROOT, "work", "script.json")
OUT = os.path.join(ROOT, "work", "speakers.json")

def categories():
    src = open(os.path.join(TMC, "include", "message.h"), encoding="utf-8").read()
    body = src[src.index("TEXT_SAVE"): src.index("} TextCategory")]
    return {name: i for i, name in enumerate(re.findall(r"(TEXT_\w+)", body))}

def who_from_file(path):
    """파일명 -> 화자 이름. script_Npc어쩌구 / src/npc/xxx.c 등. 컷신 연출 스크립트는 '컷신:' 접두"""
    base = os.path.splitext(os.path.basename(path))[0]
    base = re.sub(r"^script_", "", base)
    if base.startswith("CutsceneOrchestrator") or base.startswith("CutsceneMiscObject"):
        return "컷신:" + re.sub(r"^Cutscene(Orchestrator|MiscObject)", "", base)
    return re.sub(r"^Npc", "", base)

def collect(cat):
    refs = defaultdict(set)   # (block, msg) -> {화자}
    for f in glob.glob(os.path.join(TMC, "data", "scripts", "**", "*.inc"), recursive=True):
        for cmd, c, idx in re.findall(r"(\w*Message\w*)\s+(TEXT_\w+),\s*(0x[0-9a-fA-F]+)", open(f, encoding="utf-8").read()):
            if c in cat:
                who = "Ezlo" if cmd == "EzloMessage" else who_from_file(f)
                refs[(cat[c] + 1, int(idx, 16))].add(who)
    for f in glob.glob(os.path.join(TMC, "src", "**", "*.c"), recursive=True):
        for c, idx in re.findall(r"TEXT_INDEX\((TEXT_\w+),\s*(0x[0-9a-fA-F]+)\)", open(f, encoding="utf-8").read()):
            if c in cat:
                refs[(cat[c] + 1, int(idx, 16))].add(who_from_file(f))
    return refs

def fusers(refs, blocks):
    """조각 맞추기(합성) 대사: 코드가 합성자 ID로 대사 번호를 고르므로 TEXT_INDEX 참조가 없음 → J롬 표에서 직접 읽음
       GetFuserId(0x2632)의 엔티티 목록(적 0x232E·NPC 0x2342, 6바이트=[id,type,type2,합성자ID,이름 텍스트u16], +6부터, id=0 끝)
       + 합성자ID -> 대사 3개(제안/취소/성공) 포인터표 0x1A7C (주소 J/U 동일, 포엠·조각주머니 아저씨는 6개)"""
    rom = glob.glob(os.path.join(ROOT, "roms", "*(J).gba"))
    if not rom:
        return
    j = open(rom[0], "rb").read()
    msgs = {b["n"]: b["msgs"] for b in blocks}
    def name(t):   # 이름 텍스트 → 현재 한글(ko 우선)
        m = msgs[(t >> 8) + 1][t & 0xFF]
        return re.sub(r"<[^>]*>", "", (m["ko"] or m["kr"]).split("<start>")[0]).strip()
    for base in (0x232E, 0x2342):
        p = base + 6
        while j[p]:
            fid, nm = j[p + 3], struct.unpack_from("<H", j, p + 4)[0]
            tp = struct.unpack_from("<I", j, 0x1A7C + fid * 4)[0] - 0x8000000
            for t in struct.unpack_from("<%dH" % (6 if fid in (44, 65) else 3), j, tp):
                if nm:
                    refs[((t >> 8) + 1, t & 0xFF)].add("합성:" + name(nm))
            p += 6

# ───────── 화자 정밀화: 파일/스크립트 이름(sittingPerson, TalonGotKey…) → 실제 인물 한글 이름 ─────────
# 출처 3가지를 엮음
#   1) J롬 합성자 표: (NPC id, type, type2) -> 이름 텍스트(블록3 등) = 개인 이름(오레·모카·타론…)
#   2) data/map/entity_headers.s 의 npc_raw 배치: subtype=NPC id, paramA=type, paramB=type2, script=스크립트
#   3) src/npc/*.c 의 대사 표 배열 + 인덱스 식([this->type], [type2][..], type*N+.., NAME + type2*N)
#      → 표의 행 번호로 type/type2 를 역산 → 배치·합성자 표로 개인 이름
# 이름이 정해지면 "이름 (원래 라벨)" 로 표시(원래 라벨은 출처 확인용으로 유지)

# 합성자 표·배치로 이름이 안 나오는 NPC 종류의 기본 이름(NPC enum -> 한글)
NPC_KO = {
    "GUARD": "병사", "GUARD_1": "병사", "GUARD_WITH_SPEAR": "창병", "CASTLE_MAID": "성의 메이드",
    "KING_DALTUS": "달타스 왕", "MINISTER_POTHO": "텐가로 대신", "ZELDA": "젤다", "EZLO": "에제로",
    "EZLO_CAP": "에제로", "VAATI": "구프", "BEEDLE": "행상인", "STOCKWELL": "도구점 주인",
    "TOWN_MINISH": "마을의 픽콜", "SMALL_TOWN_MINISH": "마을의 픽콜", "FOREST_MINISH": "숲의 픽콜",
    "MOUNTAIN_MINISH": "산의 픽콜", "BLADE_BROTHERS": "텟신 형제", "TINGLE_SIBLINGS": "팅클 형제",
    "TOWNSPERSON": "마을 사람", "SITTING_PERSON": "앉아 있는 사람", "KID": "아이", "DOG": "개", "CAT": "고양이",
    "WIND_TRIBESPEOPLE": "바람의 부족", "GORON": "고론", "CARPENTER": "목수", "FARMERS": "농부",
    "TEACHERS": "선생님", "GHOST_BROTHERS": "유령 형제", "LIBRARIANS": "도서관 사서", "REM": "렘",
    "DR_LEFT": "왼손잡이 박사", "SIMON": "시몬", "ANJU": "안쥬", "EMMA": "엠마", "GORMAN": "고먼",
    "SYRUP": "시럽", "PITA": "피타", "MARCY": "마시", "MELARI": "명장 멜타", "GENTARI": "장로 젠타",
    "FESTARI": "사제 페스타", "LIBRARI": "부크타 장로", "GREGAL": "가스트 할아버지", "STURGEON": "파랑 영감",
    "COW": "소", "EPONA": "에포나", "CUCCO": "꼬꼬", "CUCCO_CHICK": "병아리 꼬꼬", "BIG_GORON": "빅 고론",
    "BOMB_MINISH": "폭탄 픽콜", "STAMP": "스탬프", "PICOLYTE_BOTTLE": "픽콜라이트", "PERCY": "포엠",
    "KING_GUSTAF": "구스타프 왕", "SIROC": "바람의 부족 장로",
}

def camel_to_enum(s):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", s).upper()

def load_npc_info(j, msgs):
    """-> (enum이름->id, id->함수이름, 합성자 항목[(id,type,type2,이름)])"""
    h = open(os.path.join(TMC, "include", "npc.h"), encoding="utf-8").read()
    body = h[h.index("enum NPC"):]
    enum = {name: int(i, 16) for i, name in re.findall(r"/\*0x([0-9a-f]+)\*/\s*(\w+)", body[:body.index("}")])}
    funcs = {}
    for e, fn in re.findall(r"\[(\w+)\]\s*=\s*\{\s*(\w+)", open(os.path.join(TMC, "src", "npcFunctions.c"), encoding="utf-8").read()):
        if e in enum:
            funcs[enum[e]] = fn
    def name(t):
        m = msgs[(t >> 8) + 1][t & 0xFF]
        return re.sub(r"<[^>]*>", "", (m["ko"] or m["kr"]).split("<start>")[0]).strip()
    fz = []
    p = 0x2342 + 6
    while j[p]:
        nm = struct.unpack_from("<H", j, p + 4)[0]
        if nm:
            fz.append((j[p], j[p + 1], j[p + 2], name(nm)))
        p += 6
    return enum, funcs, fz

def load_placements():
    """entity_headers.s 의 NPC 배치 -> [(id, type, type2, script, 방라벨)]"""
    out, room = [], ""
    for line in open(os.path.join(TMC, "data", "map", "entity_headers.s"), encoding="utf-8"):
        m = re.match(r"(Entities_\w+)::", line)
        if m:
            room = m.group(1)[9:]
        m = re.match(r"\s*npc_raw\s+(.*)", line)
        if m:
            kv = dict(re.findall(r"(\w+)=(\w+)", m.group(1)))
            out.append((int(kv["subtype"], 0), int(kv.get("paramA", "0"), 0), int(kv.get("paramB", "0"), 0),
                        kv.get("script", ""), room))
    return out

def strip_regions(src):
    """#if USA/EU/DEMO … #else … #endif 중 JP 쪽만 남김(조건에 JP 가 있으면 그 쪽)"""
    out, stack = [], []
    for line in src.split("\n"):
        s = line.strip()
        if s.startswith("#if"):
            stack.append("JP" in s or not re.search(r"USA|EU|DEMO", s)); continue
        if s.startswith("#elif"):
            stack[-1] = "JP" in s; continue
        if s.startswith("#else") and stack:
            stack[-1] = not stack[-1]; continue
        if s.startswith("#endif") and stack:
            stack.pop(); continue
        if all(stack):
            out.append(line)
    return "\n".join(out)

def split_top(body):
    """중괄호 본문 -> 최상위 요소 문자열 목록(쉼표 기준, 중첩 괄호 무시)"""
    items, depth, cur = [], 0, ""
    for ch in body:
        if ch in "{(":
            depth += 1
        elif ch in "})":
            depth -= 1
        if ch == "," and depth == 0:
            items.append(cur); cur = ""
        else:
            cur += ch
    if cur.strip():
        items.append(cur)
    return [x for x in items if x.strip()]

def table_keys(path, cat):
    """C 파일의 대사 표 배열에서 (블록,메시지) -> {(필드, 값)}  (필드 = 'type'/'type2')"""
    src = strip_regions(open(path, encoding="utf-8").read())
    res = defaultdict(set)
    for m in re.finditer(r"(?:static\s+)?const\s+(?:Dialog|u16)\s+(\w+)\s*\[[^\]]*\]\s*(\[[^\]]*\])?\s*=\s*\{", src):
        name, two_d = m.group(1), bool(m.group(2))
        i, depth = m.end(), 1          # 본문 끝 찾기
        while depth:
            depth += {"{": 1, "}": -1}.get(src[i], 0); i += 1
        body = src[m.end(): i - 1]
        ex = re.escape(name)
        if two_d:
            u = re.search(ex + r"\s*\[\s*(?:this|super)->(type2?)\s*\]", src)
            if not u:
                continue
            rows = [(g, r) for g, r in enumerate(split_top(body))]
            key = lambda g: g
        else:
            u = (re.search(ex + r"\s*\[\s*(?:this|super)->(type2?)\s*\*\s*(0x[0-9a-fA-F]+|\d+)\s*(-\s*1)?", src)
                 or re.search(ex + r"\s*\+\s*(?:this|super)->(type2?)\s*\*\s*(0x[0-9a-fA-F]+|\d+)()", src)
                 or re.search(ex + r"\s*\[\s*(?:this|super)->(type2?)\s*\]()()", src))
            if not u:
                continue
            n = int(u.group(2), 0) if u.group(2) else 1
            off = 1 if u.group(3) else 0
            rows = list(enumerate(split_top(body)))
            key = lambda r, n=n, off=off: (r + off) // n
        for r, text in rows:
            for c, idx in re.findall(r"TEXT_INDEX\((TEXT_\w+),\s*(0x[0-9a-fA-F]+)\)", text):
                if c in cat:
                    res[(cat[c] + 1, int(idx, 16))].add((u.group(1), key(r)))
    return res

def refine(refs, cat, blocks):
    rom = glob.glob(os.path.join(ROOT, "roms", "*(J).gba"))
    if not rom:
        return refs
    msgs = {b["n"]: b["msgs"] for b in blocks}
    enum, funcs, fz = load_npc_info(open(rom[0], "rb").read(), msgs)
    place = load_placements()
    ko_of_enum = {v: k for k, v in enum.items()}
    def fuser_name(nid, ty, ty2):
        for i, a, b, n in fz:
            if i == nid and a in (ty, 255) and b in (ty2, 255):
                return n
    def class_name(nid):
        ns = {n for i, a, b, n in fz if i == nid}
        e = ko_of_enum.get(nid, "")
        if e in NPC_KO:
            return NPC_KO[e]
        return ns.pop() if len(ns) == 1 else None
    def names_for(nid, field, val):
        """type/type2 값 -> 개인 이름들(배치 우선, 없으면 합성자 표 직접)"""
        out = set()
        for i, a, b, s, room in place:
            if i == nid and (a if field == "type" else b) == val:
                n = fuser_name(i, a, b)
                if n:
                    out.add(n)
        if not out:
            for i, a, b, n in fz:
                if i == nid and (a if field == "type" else b) in (val, 255):
                    out.add(n)
        return out
    # 함수이름(소문자 시작 파일명) -> NPC id,  스크립트 -> 배치 (id,type,type2)
    file2id = {fn[0].lower() + fn[1:]: i for i, fn in funcs.items()}
    script2 = defaultdict(set)
    for i, a, b, s, room in place:
        if s.startswith("script_"):
            script2[s[7:]].add((i, a, b))
    prefixes = sorted(((fn, i) for i, fn in funcs.items()), key=lambda x: -len(x[0]))
    # C 파일 대사 표 → 개인 이름
    detail = defaultdict(set)   # (block,msg,라벨) -> {이름}
    for f in glob.glob(os.path.join(TMC, "src", "npc", "*.c")):
        lab = who_from_file(f)
        nid = file2id.get(lab)
        if nid is None:
            continue
        for k, kv in table_keys(f, cat).items():
            for field, val in kv:
                detail[k + (lab,)].update(names_for(nid, field, val))
    def label_names(k, w):
        if k + (w,) in detail and detail[k + (w,)]:
            return detail[k + (w,)]
        if w in ("Ezlo", "EzloCap"):
            return {"에제로"}
        if w in file2id:                       # C 파일 = NPC 종류
            n = class_name(file2id[w]); return {n} if n else set()
        if w in script2:                       # 배치된 스크립트 -> 그 자리의 인물
            ns = {fuser_name(*t) or class_name(t[0]) for t in script2[w]} - {None}
            if ns:
                return ns
        for fn, i in prefixes:                 # 스크립트 이름 접두사 = NPC 함수 이름(TalonGotKey -> Talon)
            if w.startswith(fn) and (len(w) == len(fn) or not w[len(fn)].islower()):
                n = class_name(i); return {n} if n else set()
        return set()
    out = defaultdict(set)
    for k, ws in refs.items():
        for w in ws:
            if w.startswith("합성:") or w.startswith("컷신:"):
                out[k].add(w); continue
            ns = label_names(k, w)
            if ns:
                out[k].update("%s (%s)" % (n, w) for n in sorted(ns))
            else:
                out[k].add(w)
    return out

def propagate(refs, blocks):
    """op07/select 링크를 따라 화자 없는 대사에 출처 화자 전파(직접 참조가 우선)"""
    links = defaultdict(set)
    for b in blocks:
        for i, m in enumerate(b["msgs"]):
            for a in re.findall(r"<(?:op07|select):([0-9A-F]{4})>", m["jp"]):
                links[(b["n"], i)].add((int(a[:2], 16) + 1, int(a[2:], 16)))
    who = {k: set(v) for k, v in refs.items()}
    changed = True
    while changed:
        changed = False
        for src, dsts in links.items():
            for d in dsts:
                if src in who and d not in refs and not who[src] <= who.get(d, set()):
                    who.setdefault(d, set()).update(who[src]); changed = True
    return who

def main():
    cat = categories()
    s = json.load(open(SCRIPT, encoding="utf-8"))
    refs = collect(cat)
    fusers(refs, s["blocks"])
    refs = refine(refs, cat, s["blocks"])
    who = propagate(refs, s["blocks"])
    total = direct = linked = 0
    out = {}
    catname = {v + 1: k[5:] for k, v in cat.items()}   # 블록번호 -> 카테고리명(TEXT_ 제거)
    for b in s["blocks"]:
        for i, m in enumerate(b["msgs"]):
            if not re.sub(r"<[^>]*>|\{[^}]*\}", "", m["jp"]).strip():
                continue
            total += 1
            if (b["n"], i) in who:
                direct += (b["n"], i) in refs; linked += (b["n"], i) not in refs
                out["%d#%d" % (b["n"], i)] = sorted(who[(b["n"], i)])
            else:   # 직접 참조 없음(코드가 번호 계산, 시스템 텍스트 등) -> 블록 카테고리명만
                out["%d#%d" % (b["n"], i)] = ["[%s]" % catname.get(b["n"], "?")]
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("카테고리 %d개, 대사 %d개 중 직접 참조 %d + 링크 전파 %d = %d (%.0f%%)"
          % (len(cat), total, direct, linked, direct + linked, 100.0 * (direct + linked) / total))
    print("-> %s" % OUT)

if __name__ == "__main__":
    main()
