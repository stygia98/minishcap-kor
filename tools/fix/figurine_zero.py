# [피규어 0%] 피규어 뽑기 "1개 0%" 버그 수정 (J/U/E 공통 원본 버그, 2026-11-06)
#   python tools/fix/figurine_zero.py [롬]   (기본: 최종본 (K)_ver1.1.gba) — 이 수정만 단독 재덤프
#   검증: python tools/unicorn/test_figurine.py
#   지금 얻을 수 있는 피규어를 다 모으면(SHOP07_COMPLETE) 확률 0%인데, 최저 확률 보정
#   FigurineDevice_GetChanceBasedOffFigurineCount @0x88228 이 0%도 15/12/9/6%로 올림
#   → 당첨돼도 고를 피규어가 없어 무작위 번호(미출시 피규어 포함)가 나오고, 소지 표시만 되고
#     개수(figurineCount)는 안 늘어 컴플리트 메달을 영영 못 받음.
#   수정: 분기 4곳  movs r0,#0 / ldrsb r0,[r1,r0] / cmp r0,#N / bgt
#             →  ldrb r0,[r1] / subs r0,#1 / cmp r0,#N-1 / bhi
#   (0-1 = 부호 없는 큰 수 → 보정 건너뛰어 0% 유지 = 항상 가진 피규어 → 5루피. 1~N%는 기존과 동일)
#   점프 없이 제자리 명령 교체(32바이트 중 24바이트 변경)
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rom_stage

NAME = "피규어 뽑기 0% 상태 최저 확률 보정 제외"
PATCH = [                       # (오프셋, 기존 u16, 새 u16)
    p for base, n in ((0x88238, 0x0E), (0x8824E, 0x0B), (0x88260, 0x08), (0x8826E, 0x05))
    for p in ((base, 0x2000, 0x7808), (base + 2, 0x5608, 0x3801),
              (base + 4, 0x2800 | n, 0x2800 | (n - 1)))
] + [(0x8823E, 0xDC1C, 0xD81C), (0x88254, 0xDC11, 0xD811), (0x88266, 0xDC08, 0xD808), (0x88274, 0xDC01, 0xD801)]

def regions(rom):
    return []                   # 빈 공간 안 씀(기존 코드 제자리 교체 — 원래/새 값으로 확인)

def apply(rom):
    rom_stage.patch_u16(rom, NAME, PATCH)
    return rom

def main(src=None, dst=rom_stage.FINAL):
    return rom_stage.run("피규어 0%", regions, apply, src, dst)

if __name__ == "__main__":
    main(dst=sys.argv[1] if len(sys.argv) > 1 else rom_stage.FINAL)
