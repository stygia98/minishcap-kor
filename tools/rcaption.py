# R버튼 동작 캡션(스프라이트 322, 프레임 130~147)
#   캡션 1개 = 12타일(48x16) = 32x16 조각(타일 0~7, 4x2 행우선) + 오른쪽 16x16 조각(타일 8~11, 2x2)
#   색: 0=투명, E=글자 채움, F=테두리 (원본 K 캡션과 동일)
#
#   python tools/rcaption.py [롬]        -> work/rcaption_view.bin (YY-CHR: 4BPP GBA, 패턴 8x8)
#                                          캡션마다 3줄(윗줄 타일 0 1 2 3 8 9 / 아랫줄 4 5 6 7 10 11 / 빈 줄)
#   python tools/rcaption.py --preview   -> work/rcaption_preview.png (원본 K / 새 캡션 비교)
#   apply(rom) : dump.py 가 호출. CAPTIONS 를 대사 폰트(완성형) 글리프 + 1px 테두리로 그려 넣음
import os, sys, glob, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
SPRITE_PTRS = 0x29B4      # gSpritePtrs (J/K 동일)
SPRITE = 322
FRAMES = range(130, 148)
ORDER = [[0, 1, 2, 3, 8, 9], [4, 5, 6, 7, 10, 11]]
BLANK = b"\x00" * 32
FONT_PAGES = 0xDC9F00     # K 대사 폰트 페이지 포인터표

# 프레임 -> 캡션 (일본어판 기준 번역, 2026-11-04 사용자 결정). 130·131 은 같은 타일을 공유
#   130 なし/131 やめる 132 おく 133 なげる 134 よむ 135 チェック 136 ひらく 137 しゃべる 138 つかむ
#   139 もつ 140 大きく 141 小さく 142 ころがる 143 けってい 144 もどる 145 オプション (146·147 Cancel 유지)
CAPTIONS = {
    130: "취소", 132: "내려놓기", 133: "던지기", 134: "읽는다", 135: "조사한다", 136: "열기",
    137: "말한다", 138: "잡는다", 139: "들어올린다", 140: "커진다", 141: "작아진다", 142: "구르기",
    143: "결정한다", 144: "돌아가기", 145: "옵션",
}
W, H = 48, 16

def frames(rom):
    _, f, p, _ = struct.unpack_from("<4I", rom, SPRITE_PTRS + SPRITE * 16)
    f -= 0x8000000; p -= 0x8000000
    for k in FRAMES:
        nt, _, ft = struct.unpack_from("<BBH", rom, f + k * 4)
        yield k, nt, p + ft * 32

def tile_pos(i):
    return (i % 4, i // 4) if i < 8 else (4 + (i - 8) % 2, (i - 8) // 2)

def read_caption(rom, base):
    g = [[0] * W for _ in range(H)]
    for i in range(12):
        c, r = tile_pos(i)
        for y in range(8):
            for x in range(8):
                g[r * 8 + y][c * 8 + x] = (rom[base + i * 32 + y * 4 + x // 2] >> (4 * (x & 1))) & 15
    return g

def write_caption(rom, base, g):
    for i in range(12):
        c, r = tile_pos(i)
        for y in range(8):
            for x in range(0, 8, 2):
                rom[base + i * 32 + y * 4 + x // 2] = g[r * 8 + y][c * 8 + x] | g[r * 8 + y][c * 8 + x + 1] << 4

def font_ink(rom, ch, enc, mc):
    """대사 폰트 글자 -> 잉크(E) 좌표 목록과 잉크 폭"""
    b = mc.encode(ch, enc)
    v = ((b[0] & 7) + 1) << 8 | b[1] if len(b) == 2 else (9 + (b[1] & 0xF)) << 8 | b[2]
    base = struct.unpack_from("<I", rom, FONT_PAGES + (v >> 8 & 0xF) * 4)[0] - 0x8000000 + (v & 0xFF) * 128
    pts = []
    for t, (tx, ty) in enumerate([(0, 0), (0, 8), (8, 0), (8, 8)]):
        for y in range(8):
            for x in range(8):
                if (rom[base + t * 32 + y * 4 + x // 2] >> (4 * (x & 1))) & 15 == 0xE:
                    pts.append((tx + x, ty + y))
    x0 = min(x for x, _ in pts)
    return [(x - x0, y) for x, y in pts], max(x for x, _ in pts) - x0 + 1

def render(rom, text):
    """원본 캡션 규격: 잉크 = 대사 폰트를 한 줄 위로, 글자 사이 잉크 간격 2(테두리 맞닿음), 오른쪽 정렬(마지막 열 비움)"""
    import mc_codec as mc
    enc = mc.load_tbl(os.path.join(ROOT, "script-kor", "kor-table.tbl"))[4]
    glyphs = [font_ink(rom, ch, enc, mc) for ch in text]
    gap = 2                           # 원본 캡션처럼 이웃 글자 테두리가 맞닿는 간격
    while sum(w for _, w in glyphs) + gap * (len(glyphs) - 1) + 2 > W - 1 and gap > 1:
        gap -= 1                      # 칸이 모자라면 글자 간격을 좁힘(들어올린다 등)
    total = sum(w for _, w in glyphs) + gap * (len(glyphs) - 1)
    assert total + 2 <= W, "캡션이 48px 를 넘음: %s (%dpx)" % (text, total + 2)
    ink = set()
    x = W - 2 - total                 # 오른쪽 테두리가 46열에 오도록
    for pts, w in glyphs:
        ink |= {(x + px, py - 1) for px, py in pts}
        x += w + gap
    g = [[0] * W for _ in range(H)]
    for px, py in ink:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if 0 <= px + dx < W and 0 <= py + dy < H:
                    g[py + dy][px + dx] = 0xF
    for px, py in ink:
        g[py][px] = 0xE
    return g

def apply(rom):
    done = {}
    for k, nt, base in frames(rom):
        if k in CAPTIONS:
            assert nt == 12
            write_caption(rom, base, render(rom, CAPTIONS[k]))
            done[k] = CAPTIONS[k]
    print("  R버튼 캡션: %d개 (%s)" % (len(done), "·".join(done.values())))
    return rom

def view(rom):
    out = bytearray()
    for k, nt, base in frames(rom):
        for row in ORDER:
            for t in row:
                out += rom[base + t * 32: base + t * 32 + 32]
            out += BLANK * (16 - len(row))
        out += BLANK * 16
    return out

def preview(rom, path):
    from PIL import Image, ImageDraw
    new = apply(bytearray(rom))
    S = 4
    pal = {0: (24, 24, 40), 0xE: (255, 255, 255), 0xF: (60, 60, 200)}
    img = Image.new("RGB", (2 * W * S + 90, len(FRAMES) * (H + 2) * S), (40, 40, 40))
    d = ImageDraw.Draw(img)
    for row, ((k, _, base), (_, _, nbase)) in enumerate(zip(frames(rom), frames(new))):
        for col, (r, b) in enumerate(((rom, base), (new, nbase))):
            g = read_caption(r, b)
            for y in range(H):
                for x in range(W):
                    X, Y = col * (W * S + 40) + x * S, row * (H + 2) * S + y * S
                    d.rectangle([X, Y, X + S - 1, Y + S - 1], fill=pal.get(g[y][x], (255, 0, 0)))
        d.text((2 * W * S + 44, row * (H + 2) * S + 20), "#%d" % k, fill=(255, 120, 120))
    img.save(path)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else glob.glob(os.path.join(ROOT, "roms", "*(K)_base.gba"))[0]
    rom = open(path, "rb").read()
    if "--preview" in sys.argv:
        out = os.path.join(ROOT, "work", "rcaption_preview.png")
        preview(rom, out)
    else:
        out = os.path.join(ROOT, "work", "rcaption_view.bin")
        open(out, "wb").write(view(rom))
        for i, (k, nt, base) in enumerate(frames(rom)):
            print("%2d번째(줄 %3d~) 프레임 %d  롬 0x%X~0x%X" % (i, i * 3, k, base, base + nt * 32 - 1))
    print("->", out)
