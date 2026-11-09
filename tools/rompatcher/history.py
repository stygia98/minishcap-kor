# [패치 이력] 탭: 저장소 루트 CHANGELOG.md 내용(make_patch가 patch_data.HISTORY로 내장)을 읽기 전용으로 표시
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import patch_data as P

lines = P.HISTORY.splitlines()
VERSION = next((l[3:].split()[0] for l in lines if l.startswith("## ")), "?")   # 첫 버전 제목 = 현재 버전(창 제목에도 사용)

class App(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="현재 버전: %s    결과 CRC32 %08X" % (VERSION, P.K_CRC), anchor="w").pack(fill="x", padx=8, pady=(8, 4))
        t = ScrolledText(self, width=60, height=18, wrap="word", font=("맑은 고딕", 9))
        t.tag_configure("h", font=("맑은 고딕", 10, "bold"), spacing1=6)
        t.tag_configure("c", foreground="#1a5fb4", spacing1=3)
        for l in lines:
            if l.startswith("## "):
                t.insert("end", "■ " + l[3:] + "\n", "h")
            elif l.startswith("- ["):                       # 분류 소제목 [대사수정] 등
                t.insert("end", "  " + l[2:] + "\n", "c")
            elif l.startswith("- "):
                t.insert("end", "  · " + l[2:] + "\n")
        t.configure(state="disabled")
        t.pack(fill="both", expand=True, padx=8, pady=(0, 8))
