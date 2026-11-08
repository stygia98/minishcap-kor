# [회오리 버그] 암흑하이랄성-회오리버그수정 (2026-11-05, 추측 기반 수정 — 크래시 실기 미확인)
#   python tools/fix/dhc_whirlwind.py [롬]   (기본: 최종본 (K)_ver1.1.gba) — 이 수정만 단독 재덤프
#   검증: python tools/unicorn/test_initanim.py
#   ★ 원상복구: 아래 ENABLED = False → python tools/fix/dhc_whirlwind.py (→ 배포본은 python tools/rompatcher/build.py)
#     꺼 두면 0x426C~0x4273 이 원래 8바이트(OLD)로, 0xE57400~0xE5747F 가 FF로 돌아감(다른 패치와 독립)
#     원본 바이트 0x426C: 89 00 51 58 C1 65 5A E0 / 수정 바이트: 00 4B 18 47 01 74 E5 08 + 스텁 36바이트
# 암흑 하이랄 성 회오리 방 크래시(일부 에뮬레이터) 방지 — 원래 게임 버그
#   InitializeAnimation(0x08004260, tmc asm code_08003FC4.s): 프레임포인터 = gSpritePtrs[ent->spriteIndex].animations[animIdx]
#   애니메이션 표가 없는(NULL) 스프라이트(13~22·28·58·97: 플레이어 아이템 등)에 이 함수가 불리면
#   주소 animIdx*4(=0x38, BIOS 영역)를 읽음 → 실기는 BIOS 보호값(IRQ 직후 0xE55EC002)이 프레임포인터가 되고
#   그 주소(미사용 영역)의 오픈버스 값으로 우연히 넘어가지만, BIOS/오픈버스를 다르게 흉내 내는 에뮬레이터는
#   쓰레기 프레임 → 엉뚱한 타일 복사·점프로 멈춤/리셋. VBA-M 로그로 확인(2026-11-05):
#     Illegal word read from bios: 00000038 at 0800426c → Illegal byte read: e55ec002~5 at 0800432e~433e
#   수정: 0x426C~0x4273(lsls/ldr/str/b FrameZero)을 스텁으로 보내 표가 NULL이면 더미 프레임 사용
#     더미 = [프레임 0xFF(그래픽 갱신 안 함), 길이 0x7F, 0, 0x80(끝)] + [1](자기 자신으로 반복)
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rom_stage

ENABLED = True                     # 암흑하이랄성-회오리버그수정 켜기/끄기
STUB = 0xE57400                    # 빈 공간(_ver0.3 FF), 사용자 지정 2026-11-08 (이전 0xE57F00)
STUB_END = 0xE57480                # 이 수정 영역 끝(뒤 0xE57480~ 의식 타이머, 0xE57600~ 바아티3 낙하 수정, 2026-11-09)
OLD = bytes.fromhex("89005158c1655ae0")     # 0x426C: lsls r1,#2 / ldr r1,[r2,r1] / str r1,[r0,#0x5c] / b FrameZero

def stub():
    s = 0x8000000 + STUB
    code = struct.pack("<10H",
        0x2A00,     # +00 cmp r2,#0
        0xD002,     # +02 beq +0A (null)
        0x0089,     # +04 lsls r1,r1,#2
        0x5851,     # +06 ldr r1,[r2,r1]          (원래 동작)
        0xE000,     # +08 b +0C
        0x4902,     # +0A ldr r1,=DUMMY           (표 없음)
        0x65C1,     # +0C str r1,[r0,#0x5c]
        0x4B02,     # +0E ldr r3,=FrameZero|1
        0x4718,     # +10 bx r3
        0x46C0)     # +12 nop
    code += struct.pack("<II", s + 0x1C, 0x0800432B)               # +14 DUMMY 주소, +18 FrameZero
    code += bytes([0xFF, 0x7F, 0x00, 0x80, 0x01, 0, 0, 0])          # +1C DUMMY 프레임
    return code

def is_patched(rom):
    """0x426C 가 'ldr r3,[pc] / bx r3 / .word 스텁' 형태인지(스텁 주소는 상관없이)"""
    return rom[0x426C:0x4270] == b"\x00\x4B\x18\x47" and rom[0x4273] == 0x08

def revert(rom):
    """원상복구: 0x426C 를 원래 8바이트로, 스텁 자리는 FF로(검증 프로그램도 사용)"""
    assert bytes(rom[0x426C:0x4274]) == OLD or is_patched(rom), "InitializeAnimation 자리가 원본도 수정본도 아님"
    rom[0x426C:0x4274] = OLD
    rom[STUB:STUB_END] = b"\xFF" * (STUB_END - STUB)

def fix(rom):
    """스위치와 상관없이 수정 적용(검증 프로그램도 사용). 이미 수정된 롬이면 원래대로 돌린 뒤 다시 씀"""
    revert(rom)
    code = stub()
    assert STUB + len(code) <= STUB_END
    assert rom[STUB:STUB + len(code)] == b"\xff" * len(code), "스텁 자리가 비어 있지 않음"
    rom[STUB:STUB + len(code)] = code
    rom[0x426C:0x4274] = struct.pack("<HHI", 0x4B00, 0x4718, 0x8000000 + STUB + 1)   # ldr r3,[pc] / bx r3 / .word 스텁
    print("  버그픽스: 애니메이션 표 없는 스프라이트 BIOS 읽기 방지(암흑 하이랄 성 회오리 방 크래시)")

def regions(rom):
    return [(STUB, STUB_END)]   # 스텁 자리(원래 FF) — 0x426C 8바이트는 OLD 상수로 처리

def apply(rom):
    if ENABLED:
        fix(rom)
    else:
        revert(rom)
        print("  (암흑하이랄성-회오리버그수정 꺼짐 — 원본 코드로 되돌림)")
    return rom

def main(src=None, dst=rom_stage.FINAL):
    return rom_stage.run("회오리 버그", regions, apply, src, dst)

if __name__ == "__main__":
    main(dst=sys.argv[1] if len(sys.argv) > 1 else rom_stage.FINAL)
