# 피규어 뽑기 최저 확률 보정 패치 검증 (patches.py [5]) — unicorn으로 원본/수정 함수 실행 비교
import os, sys, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_LR, UC_ARM_REG_SP
import patches

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUNC, ENT, RET = 0x8088228, 0x3000000, 0x8000100     # 함수 / 엔티티 / 복귀 주소(그냥 멈춤 지점)

def run(rom, count, chance):
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    mu.mem_map(0x8000000, 0x1000000); mu.mem_write(0x8000000, bytes(rom))
    mu.mem_map(0x2000000, 0x40000); mu.mem_map(0x3000000, 0x8000)
    mu.mem_write(0x2002A40 + 0xB0, bytes([count]))   # gSave.stats.figurineCount
    mu.mem_write(ENT + 0x83, bytes([chance & 0xFF]))
    mu.reg_write(UC_ARM_REG_R0, ENT); mu.reg_write(UC_ARM_REG_LR, RET | 1)
    mu.reg_write(UC_ARM_REG_SP, 0x3007F00)
    mu.emu_start(FUNC | 1, RET)
    return mu.mem_read(ENT + 0x83, 1)[0]

if __name__ == "__main__":
    base = bytearray(open(os.path.join(ROOT, "roms", "The Legend of Zelda - Fushigi no Boushi(K)_base.gba"), "rb").read())
    fixed = bytearray(base)
    for off, old, new in patches.FIGURINE_ZERO_CHANCE:
        assert struct.unpack_from("<H", fixed, off)[0] == old, "기존 바이트 불일치 @0x%X" % off
        struct.pack_into("<H", fixed, off, new)
    bad = 0
    for count in (0, 49, 50, 79, 80, 109, 110, 135):
        for chance in range(0, 101):
            a, b = run(base, count, chance), run(fixed, count, chance)
            want = 0 if chance == 0 else a              # 0%만 달라야 함
            if b != want or (chance == 0 and a == 0):
                bad += 1; print("불일치 count=%d chance=%d 원본=%d 수정=%d" % (count, chance, a, b))
    print("검증 %s" % ("통과(0%만 0 유지, 1~100%는 원본과 동일)" if bad == 0 else "실패 %d건" % bad))
