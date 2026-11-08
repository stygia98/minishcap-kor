# 젤다 이상한모자 한글 패치 — 통합 도구 (탭 1: 한글 패치 / 탭 2: 세이브 플레이어 이름 수정)
#   빌드: python tools/rompatcher/build.py (실행 파일 아이콘 app.ico, 창 제목 아이콘 shell.ico 동봉)
import os, sys, tkinter as tk
from tkinter import ttk
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "name_editer"))
import romk_patcher
import name_editer

def main():
    root = tk.Tk()
    root.title(romk_patcher.TITLE)
    root.resizable(False, False)
    try:                                         # 창 제목 아이콘 = 조개(shell.ico, exe에서는 압축 해제 폴더 _MEIPASS)
        root.iconbitmap(default=os.path.join(getattr(sys, "_MEIPASS", HERE), "shell.ico"))
    except Exception:
        pass
    tabs = ttk.Notebook(root)
    tabs.add(romk_patcher.App(tabs), text="  한글 패치  ")
    tabs.add(name_editer.App(tabs), text="  세이브 이름 수정  ")
    tabs.pack(padx=6, pady=6)
    root.mainloop()

if __name__ == "__main__":
    main()
