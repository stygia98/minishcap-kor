# 대사 픽셀 폭 계산 + 줄 잘림 검사
# 근거(K롬 코드 리버싱, 0x805EE28 문자 디코더 / 0x805F09C 글리프 주소):
#   글자값 v = (page<<8)|idx
#     10~FF        -> page1, idx=byte          (8x16 반각, 64바이트)
#     0B~0E xx     -> page 4~7, idx=xx          (16x16, 128바이트)
#     0F xx (<30)  -> page2, idx=xx  /  0F 3x -> page3, idx=x
#     0F 4n xx     -> page 9+n, idx=xx          (확장 한글 3바이트)
#   페이지 주소 = [0x5F104가 가리키는 포인터표][page], page 0~2는 idx*64, 나머지 idx*128
#   글리프는 열 우선 8x8 타일(4bpp). 세로 한 열이 전부 색 F인 열은 렌더 시 잘림 -> 남은 열 수 = 폭
import os, struct, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # tools/ (mc_codec)
import mc_codec

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROM = os.path.join(ROOT, "resource", "roms", "The Legend of Zelda - Fushigi no Boushi(K)_ver1.1.gba")   # 대사 폰트(최종 롬)
TBL = os.path.join(ROOT, "resource", "script-kor", "kor-table.tbl")

LINE_MAX = 212   # 한 줄 최대 픽셀 — 실측: 212px(4#21) 정상, 213px(limit2.png) 잘림 — 조정 노브
NAME_W = 6 * 8   # <name>(플레이어 이름) 최대폭: 일본어 반각 6자(가나 최대 8px) — 조정 노브


class FontWidth:
    def __init__(self, rom_path=ROM):
        self.rom = open(rom_path, "rb").read()
        ptab = struct.unpack_from("<I", self.rom, 0x5F104)[0] & 0x1FFFFFF
        self.pages = [struct.unpack_from("<I", self.rom, ptab + i * 4)[0] & 0x1FFFFFF for i in range(17)]
        self.cache = {}

    def glyph(self, page, idx):
        """글리프 실제 폭(px). 잘림 열(전부 F) 제외."""
        key = (page, idx)
        if key not in self.cache:
            if page >= len(self.pages):  # 블록8 지역명 {0F4F}xx 등: 별도 타이틀 렌더러라 대사 폭 계산 대상 아님
                raise ValueError("대사 폰트 밖 페이지 %d" % page)
            half = page <= 2
            a = self.pages[page] + idx * (64 if half else 128)
            w = 0
            for x in range(8 if half else 16):
                t = a + (x // 8) * 64  # 열 우선: 왼쪽 2타일(상,하) 다음 오른쪽 2타일
                col = [self.rom[t + (y // 8) * 32 + (y % 8) * 4 + (x % 8) // 2] for y in range(16)]
                col = [(b >> 4) if x & 1 else b & 15 for b in col]
                w += any(v != 15 for v in col)
            self.cache[key] = w
        return self.cache[key]

    def lines(self, data):
        """메시지 바이트 -> 줄별 픽셀 폭 리스트(<BR>/<END> 기준). 게임 디코더와 같은 인자 길이로 순회."""
        out, cur, i, n = [], 0, 0, len(data)
        while i < n:
            b = data[i]; i += 1
            if b >= 0x10:
                cur += self.glyph(1, b)
            elif 0x0B <= b <= 0x0E:
                cur += self.glyph(b - 0x0B + 4, data[i]); i += 1
            elif b == 0x0F:
                s = data[i]; i += 1
                if s <= 0x2F:
                    cur += self.glyph(2, s)
                elif s <= 0x3F:
                    cur += self.glyph(3, s & 0xF)
                else:
                    cur += self.glyph((s & 0xF) + 9, data[i]); i += 1
            elif b == 0x00:  # <END> = 메시지 끝(뒤는 블록 끝 쓰레기 데이터일 수 있음)
                out.append(cur); cur = 0
                break
            elif b == 0x0A:  # <BR>
                out.append(cur); cur = 0
            elif b == 0x06:  # 06 xx (xx==5면 인자 2개 더), 06 00 = <name>
                s = data[i]; i += 1
                if s == 0:
                    cur += NAME_W
                elif s == 5:
                    i += 2
            elif b == 0x04:  # <dialogbox:xx> 04 xx, 04 10 은 인자 1개 더(<dialogalign:10YY>)
                i += 2 if data[i] == 0x10 else 1
            elif b == 0x05:  # <select> 05 FF 또는 05 xx yy
                i += 1 if data[i] == 0xFF else 2
            elif b in (0x03, 0x07):
                i += 2
            elif b in (0x01, 0x02, 0x08, 0x09):
                i += 1
        if cur:
            out.append(cur)
        return out


def scan(script_path, field="ko", limit=LINE_MAX):
    """script.json의 field 대사 중 한 줄이 limit을 넘는 것 출력. 반환: 건수"""
    one, two, three, leads, enc = mc_codec.load_tbl(TBL)
    fw = FontWidth()
    s = json.load(open(script_path, encoding="utf-8"))
    bad = 0
    for bl in s["blocks"]:
        if bl.get("special") or bl["n"] == 8:  # 8 = 지역명 타이틀(대사창 아님)
            continue
        for mi, m in enumerate(bl["msgs"]):
            text = m.get(field) or ""
            if not text:
                continue
            try:
                ws = fw.lines(mc_codec.encode(text, enc))
            except (ValueError, IndexError) as e:
                print("블록%d #%d 처리 실패: %s" % (bl["n"], mi, e)); continue
            parts = text.replace("<END>", "<BR>").split("<BR>")
            for li, w in enumerate(ws):
                if w > limit:
                    bad += 1
                    print("블록%d #%d 줄%d %dpx(+%d): %s" % (bl["n"], mi, li + 1, w, w - limit,
                                                         parts[li] if li < len(parts) else ""))
    return bad


if __name__ == "__main__":
    # 자가검증: 한글 완성형은 전부 9px, limit2.png 잘린 줄은 초과·정상 줄은 통과
    one, two, three, leads, enc = mc_codec.load_tbl(TBL)
    fw = FontWidth()
    w = lambda t: fw.lines(mc_codec.encode(t, enc))[0]
    assert w("가") == 9 and w("빎") == 9, (w("가"), w("빎"))
    cut = w("이 가게는 정말 바쁘다구， 사람들이 많이 오기 때문")
    ok = w("지도에는 이 부근에 엘레멘트가 있다는 것 같구만")
    print("공백=%d 쉼표=%d / 잘린줄=%d 정상줄=%d" % (w(" "), w("，"), cut, ok))
    assert ok <= LINE_MAX < cut
    field = sys.argv[1] if len(sys.argv) > 1 else "ko"
    print("초과 %d건" % scan(os.path.join(ROOT, "work", "script.json"), field))
