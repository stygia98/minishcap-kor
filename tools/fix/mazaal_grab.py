# [마자르 잡기] 바람의 요새 보스(마자르) 손에 잡힌 채 행동 불능이 되는 버그 수정 (2026-11-09) — 원래 게임 버그(J 공통)
#   python tools/fix/mazaal_grab.py [롬]   (기본: 최종본 (K)_ver1.1.gba) — 이 수정만 단독 재덤프
#   검증: python tools/unicorn/test_mazaal_grab.py
#   제보: 손에 잡히는 공격 중 링크가 잡힌 채(몸부림 자세) 손만 움직이기 시작하고 링크의 머리만 남아 조작 불가
#   원인(tmc mazaalBracelet.c, J/K 주소):
#     잡기 = 행동 0x18(잡음)→0x19(내려찍기 2회)→0x1A(대기). 0x1A 끝(0x0803AD50)에서만 놓아주기
#     sub_0803B798(J/K 0x0803B73C: PL_CAPTURED 해제·점프·그림 오프셋 복구)를 부름
#     그런데 MazaalBracelet_OnCollision(0x0803A12C)은 손이 맞으면(무적시간>0, 접촉 0x95/0x8E) 행동과 상관없이
#     바로 0x28(피격 후퇴)로 바꿈 → 잡고 있는 동안 맞으면(직전에 둔 폭탄 등) 놓아주지 않은 채 손만 떠남
#   수정: 손 함수표 0xCF9B4[1](OnCollision) 을 스텁(0xE57500)으로 → 손(type 0/1)이 잡기 중(0x18~0x1A)에
#         후퇴 조건으로 맞으면 정상 놓아주기(0x1A 끝)와 같은 처리(손 다시 보이기·자식 손 충돌 켜기·놓아주기)를
#         먼저 한 뒤 원래 OnCollision 으로. 그 외에는 원래 함수 그대로
import os, sys, struct
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(TOOLS, "_vendor")); sys.path.insert(0, TOOLS)
import rom_stage

NAME = "마자르 손 피격 시 잡힌 링크 놓아주기"
PTR = 0xCF9B8                      # MazaalBracelet_Functions[1]
OLD_FN = 0x0803A12D                # MazaalBracelet_OnCollision(Thumb)
RELEASE = 0x0803B73D               # sub_0803B798(J/K 0x0803B73C)
STUB = 0xE57500                    # 빈 공간(_ver0.3 FF), 사용자 지정 2026-11-09
STUB_END = 0xE57600                # 뒤는 바아티3 낙하 수정

ASM = """
    push {r4, lr}
    mov r4, r0
    ldrb r1, [r4, #0xa]
    cmp r1, #1
    bhi orig
    ldrb r1, [r4, #0xc]
    subs r1, #0x18
    cmp r1, #2
    bhi orig
    movs r1, #0x3d
    ldrsb r2, [r4, r1]
    cmp r2, #0
    ble orig
    adds r1, #4
    ldrb r2, [r4, r1]
    cmp r2, #0x95
    beq rel
    cmp r2, #0x8e
    bne orig
rel:
    ldrb r0, [r4, #0x18]
    movs r1, #3
    bics r0, r1
    adds r0, #1
    strb r0, [r4, #0x18]
    ldr r2, [r4, #0x74]
    ldrb r0, [r2, #0x10]
    movs r1, #0x80
    orrs r0, r1
    strb r0, [r2, #0x10]
    ldr r3, =%d
    bl call_r3
orig:
    mov r0, r4
    pop {r4}
    pop {r1}
    mov lr, r1
    ldr r3, =%d
    bx r3
call_r3:
    bx r3
""" % (RELEASE, OLD_FN)

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
    return rom_stage.run("마자르 잡기", regions, apply, src, dst)

if __name__ == "__main__":
    main(dst=sys.argv[1] if len(sys.argv) > 1 else rom_stage.FINAL)
