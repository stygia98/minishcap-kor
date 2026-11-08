# [바아티3 낙하] 최종 보스 3형태 팔 안에서 나온 뒤 끝없이 떨어지는 버그 수정 (2026-11-09) — 원래 게임 버그(J 공통)
#   python tools/fix/vaati3_fall.py [롬]   (기본: 최종본 (K)_ver1.1.gba) — 이 수정만 단독 재덤프
#   검증: python tools/unicorn/test_vaati3_fall.py
#   제보: 3형태에서 필드 오른쪽 아래 끝의 팔에 들어가 눈을 부수고 시간 초과로 나오자 필드 밖으로 영원히 떨어짐(조작 불가)
#   원인(tmc roomInit.c sub_StateChange_Vaati3_Main, J/K 0x0804D5D8):
#     팔에서 나와 방(ROOM_VAATI_3_0)에 다시 들어올 때 플레이어를 "들어갔던 팔의 손 위치 + y 8"로 옮김(바닥인지 확인 안 함)
#     → 손이 낭떠러지 위(바닥 밖)면 떨어짐 → 되살아나는 위치(gPlayerState.startPos = 방 진입 위치)도 같은 곳이고
#       지나온 칸 기록(path_memory)도 비어 있어 같은 자리로 → 다시 떨어짐 반복
#   방 지형(J롬 맵 해독): 352x240, 바닥 = 타일 열 1~20·행 1~11(x 16~335, y 16~191), 테두리는 구덩이(ACT_TILE_13)
#   수정: Room_Vaati3_Main 의 StateChange 포인터(0xEA914)를 스텁(0xE57600)으로 → 원래 동작 그대로 하되
#         복귀 좌표를 팔 목표 위치 제한 범위(vaatiArm.c: x 0x20~0x140, y 0x20~0xB0, 바닥 안쪽)로 제한
#   방 원점 = (0,0)(room_header map 0,0) → 절대 좌표로 제한
import os, sys, struct
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(TOOLS, "_vendor")); sys.path.insert(0, TOOLS)
import rom_stage

NAME = "바아티3 팔 복귀 낙하 방지"
PTR = 0xEA914                      # Room_Vaati3_Main + 0x1C = sub_StateChange_Vaati3_Main 포인터
OLD_FN = 0x0804D5D9                # 원래 함수(Thumb)
STUB = 0xE57600                    # 빈 공간(_ver0.3 FF), 사용자 지정 2026-11-09
STUB_END = 0xE57800                # 뒤는 엔딩롤 표
X_MIN, X_MAX, Y_MIN, Y_MAX = 0x20, 0x140, 0x20, 0xB0

ASM = """
    push {lr}
    movs r0, #0
    ldr r3, =0x0805D21D        @ Vaati3BackgroundManager_Main(NULL) — 원래 첫 동작
    bl call_r3
    ldr r2, =0x030010D8        @ &gRoomTransition.field_0x38
    ldrb r1, [r2, #0]
    lsls r1, r1, #31           @ field_0x38 & 1 (팔에서 복귀)
    beq done
    ldrb r1, [r2, #1]          @ field_0x39
    cmp r1, #0
    beq done
    ldrb r1, [r2, #4]          @ field_0x3c = 들어갔던 팔(0/1)
    cmp r1, #1
    beq arm1
    cmp r1, #0
    bne done
    ldrh r0, [r2, #0xC]        @ field_0x44/46
    ldrh r1, [r2, #0xE]
    b set
arm1:
    ldrh r0, [r2, #0x10]       @ field_0x48/4a
    ldrh r1, [r2, #0x12]
set:
    adds r1, #8                @ 원래와 같음: y + 8
    lsls r0, r0, #16
    asrs r0, r0, #16
    lsls r1, r1, #16
    asrs r1, r1, #16
    cmp r0, #%d
    bge x1
    movs r0, #%d
x1:
    ldr r3, =%d
    cmp r0, r3
    ble x2
    mov r0, r3
x2:
    cmp r1, #%d
    bge y1
    movs r1, #%d
y1:
    cmp r1, #%d
    ble y2
    movs r1, #%d
y2:
    ldr r3, =0x03001160        @ gPlayerEntity
    strh r0, [r3, #0x2e]       @ x.HALF.HI
    strh r1, [r3, #0x32]       @ y.HALF.HI
done:
    pop {r0}
    bx r0
call_r3:
    bx r3
""" % (X_MIN, X_MIN, X_MAX, Y_MIN, Y_MIN, Y_MAX, Y_MAX)

def stub():
    from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
    src = "\n".join(l.split("@")[0] for l in ASM.splitlines())      # keystone은 ASCII만 → 한글 주석 제거
    code, _ = Ks(KS_ARCH_ARM, KS_MODE_THUMB).asm(src, 0x8000000 + STUB)
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
    return rom_stage.run("바아티3 낙하", regions, apply, src, dst)

if __name__ == "__main__":
    main(dst=sys.argv[1] if len(sys.argv) > 1 else rom_stage.FINAL)
