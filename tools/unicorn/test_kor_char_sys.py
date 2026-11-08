# 이름입력 한글 개조가 적용된 롬((K)_ver1.1.gba)의 조합 로직을 unicorn으로 실제 실행해 검증

#   python tools/unicorn/test_kor_char_sys.py [롬]

import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))

ROOT = os.path.dirname(os.path.dirname(HERE))

sys.path.insert(0, os.path.join(ROOT, "tools", "_vendor"))

sys.path.insert(0, os.path.join(ROOT, "tools"))

sys.path.insert(0, os.path.join(ROOT, "tools", "kor_char_sys"))     # assets·build_kor_char_sys

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB

from unicorn.arm_const import *

import mc_codec as mc

import assets

from build_kor_char_sys import elf_symbols, BUILD



ROM = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "resource", "roms", "The Legend of Zelda - Fushigi no Boushi(K)_ver1.1.gba")

SYM = elf_symbols(os.path.join(BUILD, "kor_char_sys.elf"))

ENC = mc.load_tbl(os.path.join(ROOT, "resource", "script-kor", "kor-table.tbl"))[4]

SYL = sorted(c for c in ENC if "가" <= c <= "힣")

STOP = 0x08E5F000

NAME = 0x02002AC0



rom = bytearray(open(ROM, "rb").read())

for a in (0x08051440, 0x080A3020, 0x080A6ECC):          # 저장/효과음/메뉴전환은 bx lr로 무력화

    rom[a - 0x08000000: a - 0x08000000 + 2] = b"\x70\x47"

rom[STOP - 0x08000000: STOP - 0x08000000 + 2] = b"\xc0\x46"



uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

uc.mem_map(0x02000000, 0x40000)

uc.mem_map(0x03000000, 0x8000)

uc.mem_map(0x06000000, 0x18000)

uc.mem_map(0x08000000, 0x1000000)

uc.mem_write(0x08000000, bytes(rom))



def call(fn, r0=0):

    uc.reg_write(UC_ARM_REG_SP, 0x03007F00)

    uc.reg_write(UC_ARM_REG_LR, STOP | 1)

    uc.reg_write(UC_ARM_REG_R0, r0)

    uc.emu_start(fn | 1, STOP, count=200000)

    return uc.reg_read(UC_ARM_REG_R0)



def reset():

    uc.mem_write(NAME, bytes(8))

    uc.mem_write(0x02000007, b"\x00")                    # 언어 0(JP)



def press(code, col=3):

    uc.mem_write(0x02000081, bytes([col]))

    uc.mem_write(0x02000090, b"\x00\x00")                # a[0]=a[1]=0

    uc.mem_write(0x02001A40 + 0xC3 * 2, struct.pack("<H", 0xF000 | 2 * code))

    uc.mem_write(0x03000FF2, b"\x01\x00")                # A

    call(SYM["hk_act6"])



def jamo(s):

    for ch in s:

        press(0x80 + assets.JAMO.index(ch))



def delete():

    uc.mem_write(0x03000FF2, b"\x02\x00")                # B

    call(SYM["hk_act5"], 0)



def name():

    n = uc.mem_read(NAME, 8)

    out, p = "", 0

    while p < 8 and n[p]:

        if n[p] < 0x10:

            v = (n[p] - 1) << 8 | n[p + 1]

            out += SYL[v] if v < 2350 else assets.JAMO[v - 2350]

            p += 2

        else:

            out += "[%02X]" % n[p]; p += 1

    return out



def text(n):

    call(SYM["hk_str"], 0)

    return bytes(uc.mem_read(0x0203B800, n + 1))   # 한글 코드 안에 00이 올 수 있어 길이로 비교



CASES = [

    ("ㅎㅏㄴㄱㅡㄹ", "", "한글"),

    ("ㄷㅏㄹㄱ", "", "닭"),

    ("ㄷㅏㄹㄱㅏ", "", "달가"),

    ("ㅎㅏㄴㅏ", "", "하나"),

    ("ㄱㅗㅏ", "", "과"),

    ("ㅇㅡㅣㅅㅏ", "", "의사"),

    ("ㄸㅗㅁ", "", "또ㅁ"),           # 똠은 완성형에 없음 → 받침 거부

    ("ㄱㅏㄴㅏㄷㅏㄹㅏㅁㅏ", "", "가나다람"),  # 5번째 글자 자리 없음 → 받침만 붙고 ㅏ 거부

    ("ㅅㅓㅇ", "D", "서"),

    ("ㅅㅓㅇ", "DD", "ㅅ"),

    ("ㅅㅓㅇ", "DDD", ""),

    ("ㄷㅏㄹㄱ", "D", "달"),

    ("ㄱㅗㅏ", "D", "고"),

    ("ㄲ", "", "ㄲ"),

    ("ㅏ", "", "ㅏ"),

    ("ㅗㅏ", "", "ㅘ"),

    ("ㅣㄹㅣㅇㅋㅡ", "", "ㅣ링크"),

]



fail = 0

for seq, ops, want in CASES:

    reset(); jamo(seq)

    for op in ops: delete()

    got = name()

    ok = got == want

    fail += not ok

    print("%s %-14s %-4s → %-8s (기대 %s)" % ("OK " if ok else "XX ", seq, ops, got, want))



# 가나 + 한글 혼합, 대사 변환 바이트

reset(); press(0x10, col=0); jamo("ㄱㅏ")

want = bytes([0x10]) + ENC["가"] + bytes(1)
print("혼합:", name(), text(3).hex(), "기대", want.hex())
fail += text(3) != want
reset(); jamo("ㅎㅣㅎ")
want = ENC["히"] + bytes([0x0F, 0x46, 0x12, 0])
t = text(len(want) - 1); print("변환 히ㅎ:", t.hex(), "기대", want.hex())
fail += t != want
print("실패", fail)

sys.exit(1 if fail else 0)

