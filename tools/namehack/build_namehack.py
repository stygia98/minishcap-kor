# 이름 입력 한글 조합형 개조 빌드 + 롬 패치
#   python tools/namehack/build_namehack.py [입력롬] [출력롬]
#   기본: roms/...(K)_edit.gba → roms/...(K)_name.gba  (입력 롬은 건드리지 않음)
import os, struct, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import assets

VENDOR = os.path.join(ROOT, "tools", "_vendor")
BUILD = os.path.join(HERE, "build")
CODE_BASE = 0x08E51800          # page15 글리프 영역(0xE50000~) 중 자모 40자 뒤의 빈 곳
JAMO_FONT = 0x00E50000          # page15 = `0F 46 xx`
KEYBASE = 0x80                  # 한글 페이지에서 자모 키가 쓰는 자판 칸 코드(0x80~0xA7)
LIMIT = 0x00E58000              # page8 글리프 시작(침범 금지)

def gen_tables():
    import mc_codec as mc   # K 폰트 테이블의 완성형 2350자(코드 순 = 유니코드 순)
    enc = mc.load_tbl(os.path.join(ROOT, "script-kor", "kor-table.tbl"))[4]
    syl = sorted(c for c in enc if "가" <= c <= "힣")
    assert len(syl) == 2350 and [enc[c] for c in syl] == sorted((enc[c] for c in syl), key=lambda b: (len(b), b))
    ks2uni = [ord(c) - 0xAC00 for c in syl]
    # 한글 페이지 타일맵: 히라가나 타일맵을 바탕으로 키 칸만 교체
    rom = open(os.path.join(ROOT, "roms", "The Legend of Zelda - Fushigi no Boushi(K)_base.gba"), "rb").read()
    tm = list(struct.unpack_from("<640H", rom, 0x8FA700))
    rows = [list(range(0, 13)), list(range(13, 19)), list(range(19, 32)), list(range(32, 40)), []]
    for r in range(5):
        for k in range(13):
            code = KEYBASE + rows[r][k] if k < len(rows[r]) else 0x20
            tm[(6 + 2 * r) * 32 + 3 + 2 * k] = 0xF000 | (2 * code)
            tm[(7 + 2 * r) * 32 + 3 + 2 * k] = 0xF000 | (2 * code + 1)
    keys = b"".join(assets.key_tiles(ch) for ch in assets.JAMO)
    def arr(name, typ, vals):
        return "static const %s %s[%d] = {%s};\n" % (typ, name, len(vals), ",".join(map(str, vals)))
    h = "#define NSYL 2350\n#define NJAMO 40\n#define KEYBASE %d\n" % KEYBASE
    h += arr("ks2uni", "u16", ks2uni)
    h += "__attribute__((aligned(4))) " + arr("hangul_tm", "u16", tm)
    h += "__attribute__((aligned(4))) " + arr("key_tiles", "u8", list(keys))
    open(os.path.join(BUILD, "tables.h"), "w").write(h)

def elf_symbols(path):
    d = open(path, "rb").read()
    shoff, = struct.unpack_from("<I", d, 0x20)
    shentsize, shnum, _ = struct.unpack_from("<HHH", d, 0x2E)
    secs = [struct.unpack_from("<IIIIIIIIII", d, shoff + i * shentsize) for i in range(shnum)]
    syms = {}
    for s in secs:
        if s[1] != 2: continue                       # SHT_SYMTAB
        strtab = secs[s[6]]
        for o in range(s[4], s[4] + s[5], 16):
            nm, val, _, _, _, _ = struct.unpack_from("<IIIBBH", d, o)
            name = d[strtab[4] + nm: d.index(b"\0", strtab[4] + nm)].decode()
            if name: syms[name] = val
    return syms

def map_symbols(path):
    """lld 맵 파일에서 전역 기호 주소 (ELF 기호표가 제거되므로)"""
    syms = {}
    for line in open(path):
        f = line.split()
        if len(f) == 5 and all(c in "0123456789abcdef" for c in f[0]) and f[4].isidentifier():
            syms[f[4]] = int(f[0], 16)
    return syms

def compile_blob():
    os.makedirs(BUILD, exist_ok=True)
    gen_tables()
    ld = os.path.join(BUILD, "link.ld")
    open(ld, "w").write("SECTIONS { . = 0x%08X; .text : { *(.text*) *(.rodata*) *(.data*) } "
                        "/DISCARD/ : { *(.ARM.*) *(.comment) *(.bss*) } }\n" % CODE_BASE)
    elf, bin_ = os.path.join(BUILD, "namehack.elf"), os.path.join(BUILD, "namehack.bin")
    env = dict(os.environ, PYTHONPATH=VENDOR)
    zig = [sys.executable, "-m", "ziglang"]
    obj = os.path.join(BUILD, "namehack.o")
    subprocess.check_call(zig + ["cc", "-c", "-target", "thumb-freestanding-eabi", "-mcpu=arm7tdmi", "-Os",
                                 "-ffreestanding", "-fno-builtin", "-fno-stack-protector", "-I", BUILD,
                                 "-o", obj, os.path.join(HERE, "namehack.c")], env=env)
    subprocess.check_call(zig + ["ld.lld", "-T", ld, "--no-gc-sections", "-e", "hk_page_load", "-o", elf, obj], env=env)
    subprocess.check_call(zig + ["objcopy", "-O", "binary", elf, bin_], env=env)
    return open(bin_, "rb").read(), elf_symbols(elf)

def tramp(rom, addr, target):
    """addr의 함수 시작을 target(thumb)으로 점프하는 코드로 덮어씀 (r3 사용)"""
    o = addr - 0x08000000
    if addr % 4 == 0:
        code = bytes.fromhex("004B1847") + struct.pack("<I", target | 1)
    else:
        code = bytes.fromhex("014B1847C046") + struct.pack("<I", target | 1)
    rom[o:o + len(code)] = code

def main(src, dst):
    blob, sym = compile_blob()
    end = CODE_BASE - 0x08000000 + len(blob)
    assert end <= LIMIT, "코드 영역 초과: %x" % end
    rom = bytearray(open(src, "rb").read())
    # 0) 빈 공간 확인(자모 글리프 + 코드 영역이 전부 FF여야 함 — 재실행은 원본에서)
    assert rom[JAMO_FONT:LIMIT].count(0xFF) == LIMIT - JAMO_FONT, "page15 영역이 비어 있지 않음(이미 패치된 롬?)"
    # 1) 자모 글리프(page15) / 코드
    for j, ch in enumerate(assets.JAMO):
        rom[JAMO_FONT + j * 128: JAMO_FONT + (j + 1) * 128] = assets.font_glyph(ch)
    rom[CODE_BASE - 0x08000000: end] = blob
    # 2) [<-] 버튼 그래픽 → [한글] (언어별 4벌 모두)
    btn = assets.hangul_button(rom)
    for base in assets.BTN_SETS:
        o = base + 0x300 + assets.BTN_BACK
        rom[o:o + 320] = btn
    # 3) 페이지 순환 3 → 4 (L/R·버튼으로 4번째 페이지까지)
    assert rom[0x511FA:0x511FC] == b"\x03\x21"
    rom[0x511FA:0x511FC] = b"\x04\x21"
    # 4) 동작 점프 테이블(0x8051124): 5=지우기/한글, 6=글자, 7=탁음, 8=END
    for act, name in ((5, "st_act5"), (6, "st_act6"), (7, "st_act7"), (8, "st_act8")):
        struct.pack_into("<I", rom, 0x51124 + (act - 1) * 4, sym[name] & ~1)
    # 5) 함수 대체: 페이지 로드 / 이름 스프라이트 / 메뉴 이름
    tramp(rom, 0x08051324, sym["hk_page_load"])
    tramp(rom, 0x080505D8, sym["hk_name_draw"])
    tramp(rom, 0x080A424C, sym["hk_menu_name"])
    # 6) 대사 `06 XX` → 이름 변환 스텁 (0x805EFA2: ldr r0,[pc,#4]; bx r0; nop; .word)
    rom[0x5EFA2:0x5EFAC] = bytes.fromhex("01480047C046") + struct.pack("<I", sym["st_str"] | 1)
    open(dst, "wb").write(rom)
    print("코드 %d바이트 @%08X, 출력 %s" % (len(blob), CODE_BASE, dst))
    for k in sorted(sym):
        if k.startswith(("hk_", "st_")): print("  %-14s %08X" % (k, sym[k]))

if __name__ == "__main__":
    R = os.path.join(ROOT, "roms")
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, "The Legend of Zelda - Fushigi no Boushi(K)_edit.gba")
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(R, "The Legend of Zelda - Fushigi no Boushi(K).gba")
    main(src, dst)
