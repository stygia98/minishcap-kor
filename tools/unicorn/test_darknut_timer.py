# 의식 타이머 수정 검증 (fix/darknut_timer.py) — unicorn으로 원래 함수/스텁 실행 비교
#   사용: python tools/unicorn/test_darknut_timer.py
#   기대: 남은 값 1 + (대사창 열림 또는 이벤트 중) → 줄이지 않고 게임 오버 전환도 안 함, 그 외는 원래와 동일
import os, sys, struct
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))    # tools/
sys.path.insert(0, os.path.join(TOOLS, "_vendor")); sys.path.insert(0, TOOLS)
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC
sys.path.insert(0, os.path.join(TOOLS, "fix"))
import rom_stage, darknut_timer as dt

TIMER, AREA, RET = 0x02002ECC, 0x02033A90, 0x8000100
RESET_FLAGS, MENU_FADE_IN = 0x080532E4, 0x080A6EF0

def run(rom, timer, area, msg, prio):
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    mu.mem_map(0x8000000, 0x1000000); mu.mem_write(0x8000000, bytes(rom))
    mu.mem_map(0x2000000, 0x40000); mu.mem_map(0x3000000, 0x8000)
    mu.mem_write(TIMER, struct.pack("<I", timer)); mu.mem_write(AREA + 1, bytes([area]))
    mu.mem_write(dt.GMESSAGE, bytes([msg])); mu.mem_write(dt.GPRIORITY, bytes([prio]))
    calls = []
    def hook(uc, addr, size, _):           # 플래그 초기화·화면 전환은 호출 기록만 하고 바로 복귀
        if addr in (RESET_FLAGS, MENU_FADE_IN):
            calls.append(addr); uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    mu.hook_add(UC_HOOK_CODE, hook)
    fn = struct.unpack_from("<I", rom, dt.PTR)[0]           # 함수표가 가리키는 함수
    mu.reg_write(UC_ARM_REG_R0, TIMER); mu.reg_write(UC_ARM_REG_LR, RET | 1); mu.reg_write(UC_ARM_REG_SP, 0x3007F00)
    mu.emu_start(fn, RET)
    return struct.unpack("<I", mu.mem_read(TIMER, 4))[0], tuple(calls)

if __name__ == "__main__":
    base = rom_stage.read_final(); dt.set_ptr(base, False)           # 원래 함수 사용
    fixed = rom_stage.read_final()
    fixed[dt.STUB:dt.STUB_END] = b"\xFF" * (dt.STUB_END - dt.STUB); dt.apply(fixed)
    bad = n = 0
    for timer in (0, 1, 2, 10800):
        for area in (29, 30):
            for msg in (0, 1, 0x7F, 0x80):
                for prio in (0, 1, 2):
                    a = run(base, timer, area, msg, prio); b = run(fixed, timer, area, msg, prio); n += 1
                    wait = timer == 1 and ((msg & 0x7F) or prio)
                    want = (timer, ()) if wait else a
                    if b != want:
                        bad += 1; print("불일치 timer=%d area=%d msg=%X prio=%d 원래=%s 수정=%s" % (timer, area, msg, prio, a, b))
    print("검증 %d건 %s" % (n, "통과(대화·이벤트 중 마지막 1에서 대기, 그 외 원래와 동일)" if bad == 0 else "실패 %d건" % bad))
