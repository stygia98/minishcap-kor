# 한글 패치 통합 도구 exe 빌드 (아이콘 = app.ico·shell.ico, 불필요 모듈 제외로 용량 축소)
#   [⑤] python tools/rompatcher/build.py   → 최종 K롬에서 패치 데이터 생성(make_patch) 후 exe 빌드
#       → tools/rompatcher/dist/MinishCap_KoreanPatch.exe
import os, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(os.path.dirname(HERE), "_vendor")

# 패처가 쓰지 않는 표준 라이브러리(쓰는 것: tkinter·zlib·base64·struct·shutil). 빼면 13.5MB → 약 9MB
EXCLUDE = [
    "ssl", "_ssl", "hashlib", "_hashlib",                      # libcrypto/libssl 2.6MB
    "unicodedata", "decimal", "_decimal", "lzma", "_lzma", "bz2", "_bz2", "_zstd", "compression.zstd",
    "email", "http", "urllib", "xml", "xmlrpc", "pydoc", "pydoc_data", "unittest", "doctest",
    "sqlite3", "_sqlite3", "asyncio", "multiprocessing", "concurrent", "csv", "_csv",
    "distutils", "setuptools", "pip", "test", "lib2to3", "tomllib", "json", "_json", "pickle", "_pickle",
    "difflib", "argparse", "calendar", "gettext", "socket", "_socket", "select", "selectors",
    "ctypes", "_ctypes", "ctypes.macholib",
]

def main():
    # 패치 데이터(patch_data.py)를 지금 최종 롬 기준으로 다시 만든 뒤 빌드(자체 검증 포함)
    subprocess.check_call([sys.executable, os.path.join(HERE, "make_patch.py")], cwd=HERE)
    # 아이콘: app.ico = 실행 파일, shell.ico = 창 제목(exe에 동봉, minishcap_tool이 실행 시 읽음)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
           "--name", "MinishCap_KoreanPatch", "--icon", os.path.join(HERE, "app.ico"),
           "--add-data", os.path.join(HERE, "shell.ico") + os.pathsep + ".",
           "--paths", os.path.join(os.path.dirname(HERE), "name_editer"),
           "--distpath", os.path.join(HERE, "dist"), "--workpath", os.path.join(HERE, "build"),
           "--specpath", os.path.join(HERE, "build")]
    for m in EXCLUDE:
        cmd += ["--exclude-module", m]
    cmd.append(os.path.join(HERE, "minishcap_tool.py"))
    env = dict(os.environ, PYTHONPATH=VENDOR)
    subprocess.check_call(cmd, env=env, cwd=HERE)
    exe = os.path.join(HERE, "dist", "MinishCap_KoreanPatch.exe")
    print("완료: %s (%.1fMB)" % (exe, os.path.getsize(exe) / 1e6))

if __name__ == "__main__":
    main()
