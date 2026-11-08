# 마자르 손 잡기 수정 검증 (fix/mazaal_grab.py) — unicorn으로 원래 OnCollision / 스텁 실행 비교
#   사용: python tools/unicorn/test_mazaal_grab.py
#   기대: 잡기 중(0x18~0x1A) 후퇴 조건 피격 → 원래 결과 + 놓아주기(PL_CAPTURED 해제·손 보이기·자식 충돌), 그 외 원래와 동일
import os, sys, struct
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))    # tools/
sys.path.insert(0, os.path.join(TOOLS, "_vendor")); sys.path.insert(0, TOOLS)
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC
sys.path.insert(0, os.path.join(TOOLS, "fix"))
import rom_stage, mazaal_grab as mg

ENT, PARENT, CHILD, HAND, RET = 0x3000100, 0x3000200, 0x3000300, 0x3000400, 0x8000100
PL_CAPTURED = 0x10                                       # gPlayerState.flags 비트(tmc player.h)
SKIP = (0x080A3020, 0x08004260, 0x080042AC, 0x0804A92C)    # 소리·애니메이션·후처리: 기록만 하고 복귀

def run(rom, typ, action, iframes, contact):
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    mu.mem_map(0x8000000, 0x1000000); mu.mem_write(0x8000000, bytes(rom))
    mu.mem_map(0x2000000, 0x40000); mu.mem_map(0x3000000, 0x8000)
    e = bytearray(0x88)
    e[0xA] = typ; e[0xC] = action; e[0x10] = 0x80; e[0x18] = 0x00
    e[0x3D] = iframes & 0xFF; e[0x41] = contact
    struct.pack_into("<I", e, 0x50, PARENT); struct.pack_into("<I", e, 0x54, CHILD); struct.pack_into("<I", e, 0x74, HAND)
    mu.mem_write(ENT, bytes(e))
    gps = struct.unpack_from("<I", rom, 0x803B73C - 0x8000000 + 4 + 0x58)[0]     # 놓아주기 함수 ldr r2,[pc,#0x58]
    mu.mem_write(gps + 0x30, struct.pack("<I", 0xFFFFFFFF))                      # 플래그 전부 켠 상태(잡힘 포함)
    calls = []
    def hook(uc, addr, size, _):
        if addr in SKIP:
            calls.append(addr); uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    mu.hook_add(UC_HOOK_CODE, hook)
    fn = struct.unpack_from("<I", rom, mg.PTR)[0]
    mu.reg_write(UC_ARM_REG_R0, ENT); mu.reg_write(UC_ARM_REG_LR, RET | 1); mu.reg_write(UC_ARM_REG_SP, 0x3007F00)
    mu.emu_start(fn, RET)
    return (bytes(mu.mem_read(ENT, 0x88)), bytes(mu.mem_read(PARENT, 0x88)), bytes(mu.mem_read(HAND + 0x10, 1)),
            struct.unpack("<I", mu.mem_read(gps + 0x30, 4))[0], tuple(calls))

if __name__ == "__main__":
    base = rom_stage.read_final(); mg.set_ptr(base, False)
    fixed = rom_stage.read_final()
    fixed[mg.STUB:mg.STUB_END] = b"\xFF" * (mg.STUB_END - mg.STUB); mg.apply(fixed)
    bad = n = rel = 0
    for typ in (0, 1, 2):
        for action in (0x13, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x28, 0x2B):
            for iframes in (0, 8, -8):
                for contact in (0x95, 0x8E, 0x80, 0x15):
                    a = run(base, typ, action, iframes, contact); b = run(fixed, typ, action, iframes, contact); n += 1
                    hit = typ < 2 and 0x18 <= action <= 0x1A and iframes > 0 and contact in (0x95, 0x8E)
                    if not hit:
                        ok = a == b
                    else:
                        rel += 1
                        ok = (b[0][0xC] == a[0][0xC] == 0x28 and b[1] == a[1] and b[4] == a[4]
                              and b[0][0x18] & 3 == 1 and b[2][0] & 0x80 and not (b[3] & PL_CAPTURED) and (a[3] & PL_CAPTURED))
                    if not ok:
                        bad += 1; print("불일치 type=%d action=%X iframes=%d contact=%X" % (typ, action, iframes, contact))
    print("검증 %d건(놓아주기 %d건) %s" % (n, rel, "통과(잡기 중 피격만 놓아주고 나머지 원래와 동일)" if bad == 0 else "실패 %d건" % bad))
