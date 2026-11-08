# 바아티3 팔 복귀 낙하 방지 검증 (fix/vaati3_fall.py) — unicorn으로 원래 함수/스텁 실행 비교
#   사용: python tools/unicorn/test_vaati3_fall.py
#   기대: 바닥 안쪽(x 0x20~0x140, y 0x20~0xB0)이면 원래와 같은 좌표, 밖이면 범위 안으로 제한, 복귀가 아니면 플레이어 안 건드림
import os, sys, struct
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))    # tools/
sys.path.insert(0, os.path.join(TOOLS, "_vendor")); sys.path.insert(0, TOOLS)
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC
sys.path.insert(0, os.path.join(TOOLS, "fix"))
import rom_stage, vaati3_fall as vf

RT, PL, BGM, RET = 0x030010A0, 0x03001160, 0x0805D21C, 0x8000100

def run(rom, f38, f39, f3c, hand0, hand1, start=(0x1234, 0x5678)):
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    mu.mem_map(0x8000000, 0x1000000); mu.mem_write(0x8000000, bytes(rom))
    mu.mem_map(0x2000000, 0x40000); mu.mem_map(0x3000000, 0x8000)
    mu.mem_write(RT + 0x38, bytes([f38, f39, 0, 0, f3c]))
    mu.mem_write(RT + 0x44, struct.pack("<4H", *hand0, *hand1))
    mu.mem_write(PL + 0x2E, struct.pack("<H", start[0])); mu.mem_write(PL + 0x32, struct.pack("<H", start[1]))
    def hook(uc, addr, size, _):           # 배경 매니저 호출은 바로 복귀(이 검증과 무관)
        if addr == BGM:
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    mu.hook_add(UC_HOOK_CODE, hook, begin=BGM, end=BGM + 1)
    fn = struct.unpack_from("<I", rom, vf.PTR)[0]          # 방 구조체가 가리키는 함수
    mu.reg_write(UC_ARM_REG_LR, RET | 1); mu.reg_write(UC_ARM_REG_SP, 0x3007F00)
    mu.emu_start(fn, RET)
    return struct.unpack("<H", mu.mem_read(PL + 0x2E, 2))[0], struct.unpack("<H", mu.mem_read(PL + 0x32, 2))[0]

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

if __name__ == "__main__":
    base = rom_stage.read_final(); vf.set_ptr(base, False)          # 원래 함수 사용
    fixed = rom_stage.read_final()
    fixed[vf.STUB:vf.STUB_END] = b"\xFF" * (vf.STUB_END - vf.STUB); vf.apply(fixed)
    bad = n = 0
    pts = [(0x08, 0x08), (0x20, 0x18), (0x60, 0x50), (0xB0, 0x88), (0x110, 0x60), (0x140, 0xA8), (0x150, 0xC8), (0x15C, 0xE8), (0xFFF0, 0x10)]
    for f38, f39 in ((1, 1), (1, 3), (0, 1), (1, 0), (3, 4)):
        for f3c in (0, 1, 2):
            for h in pts:
                other = (0x110, 0x60)
                h0, h1 = (h, other) if f3c != 1 else (other, h)
                a = run(base, f38, f39, f3c, h0, h1); b = run(fixed, f38, f39, f3c, h0, h1); n += 1
                moved = (f38 & 1) and f39 and f3c in (0, 1)
                if moved:
                    sx, sy = struct.unpack("<2h", struct.pack("<2H", *a))   # 원래 결과(부호)
                    want = (clamp(sx, vf.X_MIN, vf.X_MAX) & 0xFFFF, clamp(sy, vf.Y_MIN, vf.Y_MAX) & 0xFFFF)
                else:
                    want = a                                                  # 원래와 동일(안 건드림)
                if b != want:
                    bad += 1; print("불일치 f38=%d f39=%d f3c=%d 손=%s 원래=%s 수정=%s 기대=%s" % (f38, f39, f3c, h, a, b, want))
    print("검증 %d건 %s" % (n, "통과(바닥 안은 원래와 같음, 밖은 범위 안으로, 복귀 아니면 그대로)" if bad == 0 else "실패 %d건" % bad))
