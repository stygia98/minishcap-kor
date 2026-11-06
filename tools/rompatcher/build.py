# 한글 패치 통합 도구 exe 빌드 (아이콘 생성 + 불필요 모듈 제외로 용량 축소)
#   사용: python tools/rompatcher/build.py   → tools/rompatcher/dist/MinishCap_KoreanPatch.exe
#   패치 내용을 바꿨으면 먼저 python tools/rompatcher/make_patch.py
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
    subprocess.check_call([sys.executable, os.path.join(HERE, "make_icons.py")])
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
           "--name", "MinishCap_KoreanPatch", "--icon", os.path.join(HERE, "app.ico"),
           "--paths", os.path.join(os.path.dirname(HERE), "savename"),
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
