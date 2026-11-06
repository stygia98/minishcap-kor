# 패처 exe 아이콘 생성 (빌드 전 1회, 이미지가 바뀌면 다시 실행)
#   실행 파일 아이콘 = image/TMC_Ezlo_Sprite_2.png 첫 프레임 → app.ico (16~256, 도트 그대로 확대)
#   창 제목 아이콘   = image/TMC_Mysterious_Shell_Sprite.webp → icon_data.py (PNG base64, tk.PhotoImage 용)
import os, io, base64
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(os.path.dirname(os.path.dirname(HERE)), "image")

def square(path):
    im = Image.open(path)
    im.seek(0)                                   # 애니메이션이면 첫 프레임
    im = im.convert("RGBA")
    im = im.crop(im.getbbox())                   # 투명 여백 제거
    n = max(im.size)
    sq = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    sq.paste(im, ((n - im.width) // 2, (n - im.height) // 2))
    return sq

def scaled(im, size):
    k = max(1, size // im.width)                 # 정수배 확대(도트 유지) 후 남는 부분은 투명 여백
    big = im.resize((im.width * k, im.height * k), Image.NEAREST)
    if big.width > size:
        big = im.resize((size, size), Image.NEAREST)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(big, ((size - big.width) // 2, (size - big.height) // 2))
    return out

def main():
    ezlo = square(os.path.join(IMG, "TMC_Ezlo_Sprite_2.png"))
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [scaled(ezlo, s) for s in sizes]
    frames[-1].save(os.path.join(HERE, "app.ico"), sizes=[(s, s) for s in sizes], append_images=frames[:-1])
    shell = square(os.path.join(IMG, "TMC_Mysterious_Shell_Sprite.webp"))
    with open(os.path.join(HERE, "icon_data.py"), "w", encoding="utf-8") as f:
        f.write("# 자동 생성(make_icons.py) — 창 제목 아이콘(조개) PNG\n")
        for s in (16, 32, 64):
            buf = io.BytesIO(); scaled(shell, s).save(buf, "PNG")
            f.write("SHELL_%d = %r\n" % (s, base64.b64encode(buf.getvalue()).decode()))
    print("app.ico, icon_data.py 생성")

if __name__ == "__main__":
    main()
