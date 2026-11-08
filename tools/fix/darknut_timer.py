# [의식 타이머] 최종 보스 직전 다크넛 방에서 에제로 대화 중 의식 시간 초과 → 게임 오버 대신 멈추는 버그 수정 (2026-11-09)
#   python tools/fix/darknut_timer.py [롬]   (기본: 최종본 (K)_ver1.1.gba) — 이 수정만 단독 재덤프
#   검증: python tools/unicorn/test_darknut_timer.py
#   제보: 다크넛 3마리 전투 뒤 그 방에 머물다 셀렉트로 에제로 대화를 띄운 채 세 번째 종(의식 완료, 약 3분)이 울리면
#         정상 게임 오버 화면 대신 멈춤. 대화 중이 아니면 정상 게임 오버. 원래 게임 버그(J 공통)
#   원인(tmc gameUtils.c DarknutTimerHandler, J/K 0x080532B8):
#     gSave.darknut_timer 는 GameMain_Update 맨 앞(UpdateTimerCallbacks)에서 대사창이 열려 있어도 매 프레임 줄고,
#     0이 되면 즉시 MenuFadeIn(5,6)(젤다 석화 연출 → 게임 오버)으로 전환 → 에제로 대화(대사창·이벤트 우선순위)가
#     정리되지 않은 채 연출로 넘어가 멈춤(정확한 멈춤 지점은 에뮬 미확인)
#   수정: 타이머 처리 함수표 0xFC7C8[0] 을 스텁(0xE57480)으로 → 남은 값이 1이고 대사창이 열려 있거나
#         (gMessage.state & 0x7F) 이벤트 중이면(gPriorityHandler.event_priority != 0) 이번 프레임은 줄이지 않음.
#         대화를 닫으면 바로 원래대로 0 → 정상 게임 오버. 그 외에는 원래 함수 그대로
import os, sys, struct
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(TOOLS, "_vendor")); sys.path.insert(0, TOOLS)
import rom_stage

NAME = "의식 타이머 대화 중 게임 오버 멈춤 방지"
PTR = 0xFC7C8                      # UpdateTimerCallbacks 의 sHandlers[0]
OLD_FN = 0x080532B9                # DarknutTimerHandler(Thumb)
STUB = 0xE57480                    # 빈 공간(_ver0.3 FF), 사용자 지정 2026-11-09
STUB_END = 0xE57500                # 뒤 0xE57500~ 는 마자르 잡기 수정(2026-11-09)
GMESSAGE, GPRIORITY = 0x02000050, 0x03003DC0

ASM = """
    ldr r1, [r0]
    cmp r1, #1
    bne orig
    ldr r2, =%d
    ldrb r2, [r2]
    movs r3, #0x7f
    tst r2, r3
    bne wait
    ldr r2, =%d
    ldrb r2, [r2]
    cmp r2, #0
    bne wait
orig:
    ldr r3, =%d
    bx r3
wait:
    bx lr
""" % (GMESSAGE, GPRIORITY, OLD_FN)

def stub():
    from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
    code, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(ASM, 0x8000000 + STUB)
    return bytes(code)

def set_ptr(rom, on):
    cur = struct.unpack_from("<I", rom, PTR)[0]
    new = 0x8000000 + STUB + 1
    assert cur in (OLD_FN, new), "패치 불일치 [%s] @0x%X: %08X — 중단" % (NAME, PTR, cur)
    struct.pack_into("<I", rom, PTR, new if on else OLD_FN)

def regions(rom):
    return [(STUB, STUB_END)]

def apply(rom):
    code = stub()
    assert len(code) <= STUB_END - STUB
    rom[STUB:STUB + len(code)] = code
    set_ptr(rom, True)
    print("  버그픽스: %s (스텁 %d바이트 @0x%X)" % (NAME, len(code), STUB))
    return rom

def main(src=None, dst=rom_stage.FINAL):
    return rom_stage.run("의식 타이머", regions, apply, src, dst)

if __name__ == "__main__":
    main(dst=sys.argv[1] if len(sys.argv) > 1 else rom_stage.FINAL)
