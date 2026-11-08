# 젤다 이상한 모자(한글 이름 개조판) 세이브 이름 수정기
#   .sav(EEPROM 8KB) 3개 슬롯의 이름을 게임과 같은 형식으로 고쳐 쓰고 체크섬을 다시 계산한다.
import os, shutil, struct, tkinter as tk
from tkinter import filedialog, messagebox
import charset

# 1바이트 글자(가나·영숫자·기호·공백). 0x84는 tbl에 '○'로 적혀 있으나 실제 글꼴/자판은 장음 'ー'
ONE = dict(charset.ONE, **{" ": 0x20, "ー": 0x84})
ALIAS = {"-": "－", "‐": "－", ".": "．", "~": "∼", "〜": "∼", "～": "∼"}
SYL, JAMO = charset.SYL, charset.JAMO
SYL_IDX = {c: i for i, c in enumerate(SYL)}
CODE2ONE = {v: k for k, v in ONE.items()}
NSYL, NAME_MAX, WIDTH_MAX = 2350, 8, 48

# 슬롯별 EEPROM 주소: (체크섬1, 체크섬2, 데이터1, 데이터2), 데이터 크기 0x500, 이름 = 데이터+0x80
SLOTS = [(0x30, 0x1030, 0x80, 0x1080), (0x40, 0x1040, 0x580, 0x1580), (0x50, 0x1050, 0xA80, 0x1A80)]
DATA_SIZE, NAME_OFF = 0x500, 0x80

# ---------------- 이름 인코딩 (게임 개조 코드 kor_char_sys.c와 동일 형식) ----------------
def encode(text):
    """이름 문자열 → 8바이트. 허용 범위 밖이면 ValueError"""
    out, width = bytearray(), 0
    for ch in text:
        ch = ALIAS.get(ch, ch)
        if ch in ONE:
            out.append(ONE[ch]); width += 8
        elif ch in SYL_IDX or ch in JAMO:
            v = SYL_IDX[ch] if ch in SYL_IDX else NSYL + JAMO.index(ch)
            out += bytes([1 + (v >> 8), v & 0xFF]); width += 9
        elif "가" <= ch <= "힣":
            raise ValueError("'%s'는 게임 글꼴(완성형 2350자)에 없는 글자입니다" % ch)
        else:
            raise ValueError("'%s'는 입력할 수 없는 글자입니다\n(히라가나·가타카나·영어·숫자·~ ー - . ·한글만 가능)" % ch)
    if len(out) > NAME_MAX:
        raise ValueError("너무 깁니다: %d바이트 (최대 8바이트 — 한글 4자, 가나·영문 6자)" % len(out))
    if width > WIDTH_MAX:
        raise ValueError("너무 깁니다: 폭 %dpx (최대 48px — 한글 4자, 가나·영문 6자)" % width)
    if text.strip() == "":
        raise ValueError("이름이 비어 있습니다")
    return bytes(out) + bytes(NAME_MAX - len(out))

def decode(b):
    s, p = "", 0
    while p < NAME_MAX and b[p]:
        if b[p] < 0x10:
            v = (b[p] - 1) << 8 | (b[p + 1] if p + 1 < NAME_MAX else 0)
            s += SYL[v] if v < NSYL else (JAMO[v - NSYL] if v - NSYL < len(JAMO) else "?")
            p += 2
        else:
            s += CODE2ONE.get(b[p], "?"); p += 1
    return s

# ---------------- 세이브 파일 ----------------
def checksum(data, size):
    c = 0
    for i in range(0, size, 2):
        c += struct.unpack_from("<H", data, i)[0] ^ (size - i)
    return c & 0xFFFF

class SaveFile:
    def __init__(self, path):
        raw = open(path, "rb").read()
        if len(raw) != 0x2000:
            raise ValueError("8KB(8192바이트) 세이브가 아닙니다: %d바이트" % len(raw))
        # EEPROM은 8바이트 단위로 바이트 순서가 뒤집혀 저장됨
        self.d = bytearray(b"".join(raw[i:i + 8][::-1] for i in range(0, len(raw), 8)))
        if not self.d.startswith(b"AGBZELDA:THE MINISH CAP"):
            raise ValueError("이상한 모자 세이브 파일이 아닙니다")
        self.path = path

    def used(self, i):
        return self.d[SLOTS[i][0] + 4: SLOTS[i][0] + 8] == b"3ZCM"

    def name(self, i):
        a = SLOTS[i][2] + NAME_OFF
        return bytes(self.d[a:a + NAME_MAX])

    def set_name(self, i, b):
        for st, a in ((SLOTS[i][0], SLOTS[i][2]), (SLOTS[i][1], SLOTS[i][3])):
            self.d[a + NAME_OFF: a + NAME_OFF + NAME_MAX] = b
            c = (checksum(self.d[st + 4: st + 8], 4) + checksum(self.d[a:a + DATA_SIZE], DATA_SIZE)) & 0xFFFF
            struct.pack_into("<HH", self.d, st, c, -c & 0xFFFF)

    def save(self):
        bak = self.path + ".bak"
        if not os.path.exists(bak):
            shutil.copy2(self.path, bak)
        raw = b"".join(bytes(self.d[i:i + 8][::-1]) for i in range(0, len(self.d), 8))
        open(self.path, "wb").write(raw)

# ---------------- GUI ----------------
FONT, MONO = ("맑은 고딕", 10), ("Consolas", 10)

def hexs(b):
    return " ".join("%02X" % x for x in b)

class App(tk.Frame):
    """세이브 이름 수정 화면(창 안에 넣는 프레임). 단독 실행 = 아래 __main__, 통합 도구 = rompatcher/minishcap_tool.py 두 번째 탭"""
    def __init__(self, master):
        super().__init__(master)
        self.sav = None
        top = tk.Frame(self, padx=10, pady=8); top.pack(fill="x")
        tk.Button(top, text="세이브 파일 열기…", font=FONT, command=self.open).pack(side="left")
        self.path = tk.Label(top, text="(파일 없음)", font=FONT, fg="#666", anchor="w", width=48)
        self.path.pack(side="left", padx=8)
        self.rows = []
        for i in range(3):
            f = tk.LabelFrame(self, text=" 파일 %d " % (i + 1), font=FONT, padx=10, pady=6)
            f.pack(fill="x", padx=10, pady=4)
            tk.Label(f, text="현재", font=FONT, width=7, anchor="w").grid(row=0, column=0, sticky="w")
            cur = tk.Label(f, text="-", font=FONT, width=12, anchor="w"); cur.grid(row=0, column=1, sticky="w")
            curhex = tk.Label(f, text="", font=MONO, fg="#555"); curhex.grid(row=0, column=2, sticky="w", padx=8)
            tk.Label(f, text="새 이름", font=FONT, width=7, anchor="w").grid(row=1, column=0, sticky="w")
            var = tk.StringVar()
            ent = tk.Entry(f, textvariable=var, font=FONT, width=14); ent.grid(row=1, column=1, sticky="w")
            newhex = tk.Label(f, text="", font=MONO); newhex.grid(row=1, column=2, sticky="w", padx=8)
            btn = tk.Button(f, text="적용", font=FONT, width=6, command=lambda i=i: self.apply(i))
            btn.grid(row=0, column=3, rowspan=2, padx=(10, 0))
            var.trace_add("write", lambda *_, i=i: self.preview(i))
            ent.bind("<Return>", lambda e, i=i: self.apply(i))
            self.rows.append(dict(cur=cur, curhex=curhex, var=var, ent=ent, newhex=newhex, btn=btn))
        rng = tk.LabelFrame(self, text=" 입력 범위 ", font=FONT, padx=10, pady=6)
        rng.pack(fill="x", padx=10, pady=4)
        tk.Label(rng, text="히라가나 · 카타카나 · 영어 · 한글(완성형 2350자)\n"
                           "특수문자4개 (ー 장음)(~ 물결)(- 하이픈)(. 마침표)\n"
                           "한글로 변경시 일본어판에서는 깨져나옵니다",
                 font=FONT, fg="#333", justify="left", anchor="w").pack(fill="x")
        # 설명(왼쪽) + [파일에 저장](오른쪽) 한 줄
        bot = tk.Frame(self, padx=10, pady=8); bot.pack(fill="x")
        self.status = tk.Label(bot, text="세이브 파일(.sav)을 여세요.", font=FONT, fg="#555", anchor="w")
        self.status.pack(side="left")
        self.savebtn = tk.Button(bot, text="파일에 저장", font=FONT, command=self.save, state="disabled")
        self.savebtn.pack(side="right")
        self.refresh()

    def refresh(self):
        for i, r in enumerate(self.rows):
            used = self.sav is not None and self.sav.used(i)
            if used:
                b = self.sav.name(i)
                r["cur"].config(text=decode(b) or "(빈 이름)"); r["curhex"].config(text=hexs(b))
            else:
                r["cur"].config(text="(비어 있음)" if self.sav else "-"); r["curhex"].config(text="")
            st = "normal" if used else "disabled"
            r["ent"].config(state=st); r["btn"].config(state=st)

    def preview(self, i):
        r = self.rows[i]
        if not r["var"].get():
            r["newhex"].config(text="", fg="black"); return
        try:
            r["newhex"].config(text=hexs(encode(r["var"].get())), fg="#06c")
        except ValueError as e:
            r["newhex"].config(text=str(e).split("\n")[0], fg="#c00")

    def open(self):
        p = filedialog.askopenfilename(title="세이브 파일 선택", filetypes=[("GBA 세이브", "*.sav"), ("모든 파일", "*.*")])
        if not p: return
        try:
            self.sav = SaveFile(p)
        except (OSError, ValueError) as e:
            messagebox.showerror("열기 실패", str(e)); return
        self.path.config(text=p, fg="black")
        for r in self.rows: r["var"].set("")
        self.savebtn.config(state="disabled")
        self.status.config(text="열었습니다. 이름을 입력하고 [적용] → [파일에 저장]")
        self.refresh()

    def apply(self, i):
        try:
            b = encode(self.rows[i]["var"].get())
        except ValueError as e:
            messagebox.showerror("입력 오류", str(e)); return
        self.sav.set_name(i, b)
        self.rows[i]["var"].set("")
        self.savebtn.config(state="normal")
        self.status.config(text="파일 %d 이름 변경됨 (아직 저장 안 됨)" % (i + 1))
        self.refresh()

    def save(self):
        try:
            self.sav.save()
        except OSError as e:
            messagebox.showerror("저장 실패", str(e)); return
        self.savebtn.config(state="disabled")
        self.status.config(text="저장 완료 (원본은 .sav.bak으로 1회 백업)")
        messagebox.showinfo("저장 완료", "저장했습니다.\n원본 백업: %s.bak\n\n에뮬레이터가 켜져 있으면 끈 뒤에 다시 여세요." % os.path.basename(self.sav.path))

if __name__ == "__main__":
    root = tk.Tk()
    root.title("MinishCap_NameEditer")
    root.resizable(False, False)
    App(root).pack()
    root.mainloop()
