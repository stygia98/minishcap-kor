# 미니쉬 캡 대사 코덱: thingy .tbl 로드 + 블록(포인터테이블+본문) 디코딩/인코딩
# 블록 포맷: [32비트 LE 오프셋 테이블][메시지 본문...]  (오프셋은 블록 선두 기준)
# 토큰 규칙: <tag> = 테이블의 이름코드, <cmd:HEX> = 인자 있는 제어명령(명령+인자 통째),
#            {XX}/{XXXX} = 테이블에 없는 원시 바이트
import io, re, struct

TOKEN = re.compile(r"<[^<>]+>|\{[0-9A-Fa-f]{2}(?:[0-9A-Fa-f]{2})?\}")

def load_tbl(path):
    """.tbl -> (one, two, three, leads, enc)
    one:{byte:str} 1바이트, two:{0xHHLL:str} 2바이트, three:{0xHHMMLL:str} 3바이트(확장 한글 0F40xx 등),
    leads: 2바이트 코드의 선두바이트 집합, enc:{str:bytes} 역방향(코드가 여럿이면 첫 항목)"""
    one, two, three, leads, enc = {}, {}, {}, set(), {}
    with io.open(path, "r", encoding="cp949") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if len(k) == 2:
                b = int(k, 16); one[b] = v; enc.setdefault(v, bytes([b]))
            elif len(k) == 4:
                c = int(k, 16); two[c] = v; leads.add(c >> 8)
                enc.setdefault(v, bytes([c >> 8, c & 0xFF]))
            elif len(k) == 6:
                c = int(k, 16); three[c] = v; leads.add(c >> 16)
                enc.setdefault(v, bytes([c >> 16, (c >> 8) & 0xFF, c & 0xFF]))
    return one, two, three, leads, enc

# 인자 있는 제어명령(게임 디코더 0x805EE28 기준, J/K 동일): 명령+인자를 토큰 하나 <이름:인자HEX>로 묶음
CMD = {0x01: "op01", 0x02: "color", 0x03: "sound", 0x04: "center", 0x05: "select",
       0x06: "var", 0x07: "op07", 0x08: "op08", 0x09: "op09"}
CMD_OP = {v: k for k, v in CMD.items()}
CMD_TOK = re.compile(r"<([a-z0-9]+):([0-9A-F]+)>")

def cmd_arglen(op, first):
    """명령 op의 인자 바이트 수(first = 첫 인자 바이트)"""
    if op in (0x03, 0x07):
        return 2
    if op == 0x04:   # 04 10 은 인자 하나 더
        return 2 if first == 0x10 else 1
    if op == 0x05:   # 05 FF 만 인자 1개
        return 1 if first == 0xFF else 2
    if op == 0x06:   # 06 05 는 인자 2개 더
        return 3 if first == 0x05 else 1
    return 1

def decode(data, one, two, three, leads):
    out = []; i = 0; n = len(data)
    while i < n:
        b = data[i]
        if b in CMD and i + 1 < n and i + 1 + cmd_arglen(b, data[i+1]) <= n:
            arg = data[i+1: i+1+cmd_arglen(b, data[i+1])]
            name = two.get((b << 8) | arg[0]) if len(arg) == 1 else None
            if b == 0x06 and arg == b"\x00":
                out.append("<name>")
            elif b == 0x02 and name:   # 색상은 테이블 이름 유지(<red> 등)
                out.append(name)
            else:
                out.append("<%s:%s>" % (CMD[b], arg.hex().upper()))
            i += 1 + len(arg); continue
        if b in leads:
            # 3바이트 우선, 다음 2바이트, 그다음 원시
            if i + 2 < n and ((b << 16) | (data[i+1] << 8) | data[i+2]) in three:
                out.append(three[(b << 16) | (data[i+1] << 8) | data[i+2]]); i += 3; continue
            if i + 1 < n and ((b << 8) | data[i+1]) in two:
                out.append(two[(b << 8) | data[i+1]]); i += 2; continue
            if i + 1 < n:
                out.append("{%04X}" % ((b << 8) | data[i+1])); i += 2; continue
        out.append(one.get(b, "{%02X}" % b))
        i += 1
    return "".join(out)

def encode(text, enc):
    """토큰/글자 문자열 -> 바이트. 알 수 없는 토큰/글자는 ValueError."""
    out = bytearray(); i = 0; n = len(text)
    # 이름토큰(<...>)은 길이가 가변이라 가장 긴 매칭부터: enc 키 중 <...> 들을 길이 내림차순
    names = sorted((k for k in enc if k.startswith("<") and k.endswith(">")), key=len, reverse=True)
    while i < n:
        ch = text[i]
        if ch == "{":  # 원시 바이트 {XX} 또는 {XXXX}
            j = text.index("}", i)
            out += bytes.fromhex(text[i+1:j])  # 2자리->1바이트, 4자리->2바이트
            i = j + 1
            continue
        if ch == "<":  # 명령 토큰 <이름:인자HEX> 또는 이름 토큰
            mt = CMD_TOK.match(text, i)
            if mt and mt.group(1) in CMD_OP:
                op, arg = CMD_OP[mt.group(1)], bytes.fromhex(mt.group(2))
                if not arg or len(arg) != cmd_arglen(op, arg[0]):
                    raise ValueError("명령 인자 길이 오류: %r" % mt.group(0))
                out += bytes([op]) + arg; i = mt.end(); continue
            for name in names:
                if text.startswith(name, i):
                    out += enc[name]; i += len(name); break
            else:
                if "<" not in enc:
                    raise ValueError("미지의 태그: %r (위치 %d)" % (text[i:i+12], i))
                out += enc["<"]; i += 1   # 태그가 아니면 '<' 글자 자체
            continue
        if ch in enc:
            out += enc[ch]; i += 1; continue
        raise ValueError("테이블에 없는 글자: %r (U+%04X)" % (ch, ord(ch)))
    return bytes(out)

def parse_block(data):
    """블록 바이트 -> (포인터리스트, [메시지바이트...])"""
    first = struct.unpack_from("<I", data, 0)[0]
    cnt = first // 4
    ptrs = [struct.unpack_from("<I", data, j*4)[0] for j in range(cnt)]
    msgs = [data[ptrs[k]: (ptrs[k+1] if k+1 < cnt else len(data))] for k in range(cnt)]
    return ptrs, msgs

# 원본 K롬 디렉토리 오류 보정: 블록76(index75) 엔트리가 실제 포인터 테이블보다 0x90 뒤(0x42BC0)를 가리킴
# → 게임에서 TEXT_TOWN_MINISH2 대사가 깨짐. 실제 시작 0x42B30(첫 포인터 0xA4=41메시지, cut(k) Untitled76 일치)
K_DIR_FIX = {75: 0x42B30}

def k_split(rom, base, last_len):
    """원본 K롬 대사 영역 -> [블록 바이트 x80] (디렉토리 오류 보정, 마지막 블록 끝은 last_len)"""
    dirs = [struct.unpack_from("<I", rom, base + i*4)[0] for i in range(80)]
    for i, v in K_DIR_FIX.items():
        dirs[i] = v
    ends = dirs[1:] + [dirs[79] + last_len]
    return [rom[base + s: base + e] for s, e in zip(dirs, ends)]

def build_block(msgs):
    """[메시지바이트...] -> 블록 바이트 (포인터테이블 재계산)"""
    cnt = len(msgs)
    head = cnt * 4
    ptrs = []; off = head
    for m in msgs:
        ptrs.append(off); off += len(m)
    out = bytearray()
    for p in ptrs:
        out += struct.pack("<I", p)
    for m in msgs:
        out += m
    return bytes(out)
