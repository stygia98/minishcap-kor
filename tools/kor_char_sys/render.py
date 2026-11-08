# 타일맵+타일셋 → PNG (회색조, 4bpp) : 버튼 그래픽 위치 확인용
import os, struct, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx import K, group
def tile(buf, off):
    px = []
    for y in range(8):
        row = buf[off + y * 4: off + y * 4 + 4]
        px.append([(b >> s) & 0xF for b in row for s in (0, 4)])
    return px
def render(tm_src, tiles_src, tiles_len, out, tile_base=0):
    tm = struct.unpack_from("<640H", K, tm_src)
    tiles = K[tiles_src: tiles_src + tiles_len]
    img = Image.new("L", (256, 160))
    for i, t in enumerate(tm):
        n, hf, vf = (t & 0x3FF) - tile_base, t >> 10 & 1, t >> 11 & 1
        if n < 0 or n * 32 >= len(tiles): continue
        px = tile(tiles, n * 32)
        for y in range(8):
            for x in range(8):
                v = px[7 - y if vf else y][7 - x if hf else x]
                img.putpixel(((i % 32) * 8 + x, (i // 32) * 8 + y), v * 17)
    img.resize((768, 480), Image.NEAREST).save(out)
if __name__ == "__main__":
    g5 = group(5)
    for gi in (7, 8):
        e = group(gi)[0]
        for t in g5[:3]:
            render(e["src"], t["src"], t["size"], sys.argv[1] + "/g%d_%x.png" % (gi, t["dest"]))
