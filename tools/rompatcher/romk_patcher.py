# 젤다의 전설 이상한 모자 한글판 롬 패처
#   일본어판 원본 롬(J)을 고르면, 내장된 변경분을 덮어써서 새 한글판(K) 롬 파일을 만든다(원본은 그대로 둠).
#   원본 CRC32 가 맞지 않으면 진행하지 않고, 결과 CRC32 도 검증한다.
import os, zlib, struct, base64, tkinter as tk
from tkinter import filedialog, messagebox
import patch_data as P

TITLE = "젤다 이상한모자 한글 패치"

README = (
    "[ 한글 패치 방법 ]\n"
    "  1. ① [찾아보기…]로 일본어판 원본 롬(.gba)을 선택합니다.\n"
    "     (젤다의 전설 이상한 모자 일본판 · CRC32 %08X)\n"
    "  2. ② 저장할 위치와 파일 이름을 확인합니다(바꾸려면 [저장 위치…]).\n"
    "  3. [③ 패치하기]를 누르면 한글판 롬이 새로 만들어집니다.\n"
    "     원본 롬 파일은 그대로 남습니다.\n"
    "\n"
    "[ 세이브 파일 이름 수정 방법 ]  ─  위의 [세이브 이름 수정] 탭\n"
    "  1. [세이브 파일 열기…]로 .sav 파일을 엽니다.\n"
    "     (에뮬레이터를 끈 상태에서 하세요)\n"
    "  2. 바꿀 파일(1~3)의 [새 이름]에 이름을 입력하고 [적용]을 누릅니다.\n"
    "     한글 4자 / 가나·영문 6자까지 입력할 수 있습니다.\n"
    "  3. [파일에 저장]을 누르면 저장됩니다.\n"
    "     처음 저장할 때 원본이 .sav.bak 으로 백업됩니다.\n"
    "  ※ 한글 이름은 일본어판 롬에서는 깨져 보입니다."
)

def crc_of(data):
    return zlib.crc32(data) & 0xFFFFFFFF

def build(j):
    body = zlib.decompress(base64.b64decode("".join(P.DATA)))
    assert body[:4] == b"MCKP", "패치 데이터 손상"
    out = bytearray(j[:P.K_SIZE].ljust(P.K_SIZE, b"\0"))
    p = 4
    while p < len(body):
        off, ln = struct.unpack_from("<II", body, p); p += 8
        out[off:off + ln] = body[p:p + ln]; p += ln
    return bytes(out)

class App(tk.Frame):
    """한글 패치 화면(창 안에 넣는 프레임). 단독 실행 = 아래 __main__, 통합 도구 = minishcap_tool.py 첫 번째 탭"""
    def __init__(self, master):
        super().__init__(master)
        f = tk.Frame(self, padx=14, pady=12)
        f.pack(fill="both", expand=True)
        f.rowconfigure(6, weight=1)
        f.columnconfigure(0, weight=1)
        tk.Label(f, text="① 일본어판 원본 롬(.gba)", anchor="w").grid(row=0, column=0, columnspan=2, sticky="w")
        self.src = tk.StringVar()
        tk.Entry(f, textvariable=self.src, width=60).grid(row=1, column=0, sticky="we")
        tk.Button(f, text="찾아보기…", command=self.pick_src).grid(row=1, column=1, padx=(6, 0))
        tk.Label(f, text="② 만들 한글판 롬", anchor="w").grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.dst = tk.StringVar()
        tk.Entry(f, textvariable=self.dst, width=60).grid(row=3, column=0, sticky="we")
        tk.Button(f, text="저장 위치…", command=self.pick_dst).grid(row=3, column=1, padx=(6, 0))
        # 설명(왼쪽) + [③ 패치하기](오른쪽) 한 줄
        line = tk.Frame(f)
        line.grid(row=4, column=0, columnspan=2, sticky="we", pady=(14, 4))
        self.msg = tk.StringVar(value="원본 CRC32 %08X 인 일본어판 롬이 필요합니다" % P.J_CRC)
        tk.Label(line, textvariable=self.msg, fg="#444", anchor="w").pack(side="left")
        tk.Button(line, text="③ 패치하기", width=20, command=self.run).pack(side="right")
        # 아래 빈 공간 = 사용 설명(통합 도구에서는 세이브 탭 높이만큼 늘어남)
        rm = tk.LabelFrame(f, text=" Read Me ", padx=10, pady=6)
        rm.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        tk.Label(rm, text="[한글화:stygia]", fg="#666", anchor="e").pack(side="bottom", fill="x")
        tk.Label(rm, text=README % P.J_CRC, justify="left", anchor="nw", fg="#333").pack(fill="both", expand=True)

    def pick_src(self):
        path = filedialog.askopenfilename(title="일본어판 원본 롬 선택", filetypes=[("GBA 롬", "*.gba"), ("모든 파일", "*.*")])
        if path:
            self.src.set(path)
            if not self.dst.get():
                self.dst.set(os.path.join(os.path.dirname(path), "The Legend of Zelda - Fushigi no Boushi(K).gba"))

    def pick_dst(self):
        path = filedialog.asksaveasfilename(title="한글판 롬 저장", defaultextension=".gba",
                                            initialfile="The Legend of Zelda - Fushigi no Boushi(K).gba", filetypes=[("GBA 롬", "*.gba")])
        if path:
            self.dst.set(path)

    def run(self):
        src, dst = self.src.get().strip(), self.dst.get().strip()
        if not src or not os.path.isfile(src):
            return messagebox.showwarning(TITLE, "일본어판 원본 롬을 선택하세요")
        if not dst:
            return messagebox.showwarning(TITLE, "저장할 파일 이름을 정하세요")
        if os.path.abspath(src) == os.path.abspath(dst):
            return messagebox.showwarning(TITLE, "원본과 다른 파일 이름으로 저장하세요")
        j = open(src, "rb").read()
        c = crc_of(j)
        if len(j) != P.J_SIZE or c != P.J_CRC:
            return messagebox.showerror(TITLE, "맞는 원본 롬이 아닙니다.\n\n선택한 파일: %d바이트, CRC32 %08X\n필요한 원본: %d바이트, CRC32 %08X\n\n"
                                        "젤다의 전설 이상한 모자(일본판, 1743) 원본을 사용하세요." % (len(j), c, P.J_SIZE, P.J_CRC))
        if os.path.exists(dst) and not messagebox.askyesno(TITLE, "이미 있는 파일입니다. 덮어쓸까요?\n\n" + dst):
            return
        try:
            out = build(j)
        except Exception as e:
            return messagebox.showerror(TITLE, "패치 중 오류: %s" % e)
        if crc_of(out) != P.K_CRC:
            return messagebox.showerror(TITLE, "결과 검증 실패(CRC32 %08X, 기대 %08X)" % (crc_of(out), P.K_CRC))
        open(dst, "wb").write(out)
        self.msg.set("완료: CRC32 %08X" % P.K_CRC)
        messagebox.showinfo(TITLE, "한글 패치가 완료 되었습니다.\n\n%s\nCRC32 %08X" % (dst, P.K_CRC))

if __name__ == "__main__":
    root = tk.Tk()
    root.title(TITLE)
    root.resizable(False, False)
    App(root).pack()
    root.mainloop()
