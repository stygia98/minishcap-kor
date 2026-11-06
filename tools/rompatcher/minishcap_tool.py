# 젤다 이상한모자 한글 패치 — 통합 도구 (탭 1: 한글 패치 / 탭 2: 세이브 플레이어 이름 수정)
#   빌드: cd tools/rompatcher && python make_icons.py && PYTHONPATH=../_vendor python -m PyInstaller --noconfirm --onefile --windowed
#         --name MinishCap_KoreanPatch --icon <절대경로>/app.ico --paths ../savename --distpath dist --workpath build --specpath build minishcap_tool.py
import os, sys, tkinter as tk
from tkinter import ttk
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "savename"))
import romk_patcher
import savename

def main():
    root = tk.Tk()
    root.title(romk_patcher.TITLE)
    root.resizable(False, False)
    try:                                         # 창 제목 아이콘 = 조개(icon_data.py, make_icons.py 로 생성)
        import icon_data
        root._icons = [tk.PhotoImage(data=getattr(icon_data, "SHELL_%d" % s)) for s in (64, 32, 16)]
        root.iconphoto(True, *root._icons)
    except Exception:
        pass
    tabs = ttk.Notebook(root)
    tabs.add(romk_patcher.App(tabs), text="  한글 패치  ")
    tabs.add(savename.App(tabs), text="  세이브 이름 수정  ")
    tabs.pack(padx=6, pady=6)
    root.mainloop()

if __name__ == "__main__":
    main()
