# [세이브 체크섬] 세이브 상태 체크섬 0x0 오판 버그 수정  (출처: ARHafer/TMC_Bug-Fix-and-Analysis)
#   python tools/fix/save_checksum.py [롬]   (기본: 최종본 (K)_ver1.1.gba) — 이 수정만 단독 재덤프
#   ParseSaveFileStatus @0x7CF64, 'MCZ3' 케이스:
#     기존: (checksum1 + checksum2) == 0x10000  → checksum1=0,checksum2=0 세이브를 손상 오판
#     수정: (checksum1 + checksum2) & 0xFFFF == 0  ( = checksum2 == (u16)(-checksum1) )
#   0x7CF90 adds r0,r0,r1  (합, 유지)
#   0x7CF92 movs r1,#0x80  → lsls r0,r0,#16
#   0x7CF94 lsls r1,r1,#9  → lsrs r0,r0,#16   (r0 = 합 & 0xFFFF)
#   0x7CF98 cmp  r0,r1     → cmp  r0,#0
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rom_stage

NAME = "세이브 체크섬 0x0 손상 오판 수정"
PATCH = [                       # (오프셋, 기존 u16, 새 u16)
    (0x7CF92, 0x2180, 0x0400),
    (0x7CF94, 0x0249, 0x0C00),
    (0x7CF98, 0x4288, 0x2800),
]

def regions(rom):
    return []                   # 빈 공간 안 씀(기존 코드 제자리 교체 — 원래/새 값으로 확인)

def apply(rom):
    rom_stage.patch_u16(rom, NAME, PATCH)
    return rom

def main(src=None, dst=rom_stage.FINAL):
    return rom_stage.run("세이브 체크섬", regions, apply, src, dst)

if __name__ == "__main__":
    main(dst=sys.argv[1] if len(sys.argv) > 1 else rom_stage.FINAL)
