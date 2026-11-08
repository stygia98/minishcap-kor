# fix/dhc_whirlwind.py [회오리 버그] 검증: InitializeAnimation(0x08004260)을 unicorn으로 실제 실행
#   ① 애니메이션 표 없는 스프라이트: 원본 = BIOS(0x38) 읽기 발생 / 수정 = 읽기 없음 + 더미 프레임(0xFF)
#   ② 표 있는 스프라이트: 원본과 수정의 엔티티 결과가 바이트 단위로 동일
#   ③ 더미 프레임에서 GetNextFrame 300회 반복해도 안전
#   사용: python tools/unicorn/test_initanim.py
import os, sys, glob, struct
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # tools/
sys.path.insert(0, os.path.join(HERE, "_vendor")); sys.path.insert(0, HERE)
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_MEM_READ, UcError
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR
sys.path.insert(0, os.path.join(HERE, "fix"))
import dhc_whirlwind

ROOT = os.path.dirname(HERE)
ENT = 0x2000100
DONE = 0x8000100            # 돌아올 주소(실행 끝 표시)

def machine(rom):
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    mu.mem_map(0x0, 0x4000)                   # BIOS 영역(0으로 채움 — 읽혔는지만 본다)
    mu.mem_map(0x2000000, 0x40000); mu.mem_map(0x3000000, 0x8000)
    mu.mem_map(0x8000000, 0x1000000); mu.mem_write(0x8000000, bytes(rom))
    low = []
    mu.hook_add(UC_HOOK_MEM_READ, lambda uc, acc, addr, size, val, ud: low.append(addr), begin=0, end=0x3FFF)
    return mu, low

def call(mu, fn, r0, r1=0):
    mu.reg_write(UC_ARM_REG_R0, r0); mu.reg_write(UC_ARM_REG_R1, r1)
    mu.reg_write(UC_ARM_REG_SP, 0x3007F00); mu.reg_write(UC_ARM_REG_LR, DONE | 1)
    mu.emu_start(fn | 1, DONE, count=5000)

def init_anim(rom, sprite, anim):
    mu, low = machine(rom)
    mu.mem_write(ENT, bytes(0x90)); mu.mem_write(ENT + 0x12, struct.pack("<H", sprite))
    err = None
    try:
        call(mu, 0x8004260, ENT, anim)
    except UcError as e:
        err = str(e)
    return bytes(mu.mem_read(ENT, 0x90)), low, err, mu

def main():
    # 최종 (K)_ver1.1.gba에서 이 수정만 원래대로 돌린 것 = 원본, 다시 적용한 것 = 수정본
    import rom_stage
    base = rom_stage.read_final(); dhc_whirlwind.revert(base)
    fixed = bytearray(base); dhc_whirlwind.fix(fixed)
    null_sprites = [n for n in range(0x200) if struct.unpack_from("<I", base, 0x29B4 + n * 16)[0] == 0
                    and struct.unpack_from("<I", base, 0x29B4 + n * 16 + 8)[0] >> 24 in (8, 9)]
    # ① 표 없는 스프라이트 + 애니 14(로그의 0x38)
    _, low0, err0, _ = init_anim(base, 21, 14)
    e1, low1, err1, mu = init_anim(fixed, 21, 14)
    print("① 원본: BIOS 읽기", [hex(a) for a in low0[:2]], "오류" if err0 else "")
    assert 0x38 in low0, "원본에서 BIOS 0x38 읽기가 재현되지 않음"
    ptr = struct.unpack_from("<I", e1, 0x5C)[0]
    assert not low1 and err1 is None, (low1, err1)
    assert e1[0x1E] == 0xFF and ptr == 0x8000000 + dhc_whirlwind.STUB + 0x1C, (e1[0x1E], hex(ptr))
    print("   수정: BIOS 읽기 없음, 프레임 0x%02X, 프레임포인터 0x%X" % (e1[0x1E], ptr))
    # ③ 더미 프레임 반복
    for _ in range(300):
        call(mu, 0x8004274, ENT)
    e3 = bytes(mu.mem_read(ENT, 0x90))
    assert e3[0x1E] == 0xFF and struct.unpack_from("<I", e3, 0x5C)[0] == ptr
    print("③ GetNextFrame 300회: 프레임 0xFF 유지, 포인터 고정")
    # ② 표 있는 스프라이트 전부 × 애니 0~3: 원본 == 수정
    n = 0
    for sp in range(0x200):
        a = struct.unpack_from("<I", base, 0x29B4 + sp * 16)[0]
        if a >> 24 not in (8, 9):
            continue
        for anim in range(4):
            r0 = init_anim(base, sp, anim); r1 = init_anim(fixed, sp, anim)
            if r0[2] is None:                 # 원본이 정상 실행된 경우만 비교
                assert r0[0] == r1[0], (sp, anim)
                n += 1
    print("② 표 있는 스프라이트 %d건: 원본과 결과 동일" % n)
    print("애니메이션 표 없는 스프라이트:", null_sprites)
    print("검증 통과")

if __name__ == "__main__":
    main()
