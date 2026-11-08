# 덤프 단계 공용: 롬 경로 + "(K)_ver1.1.gba 읽기 → 이 단계 빈 공간 FF로 지움 → 적용 → (K)_ver1.1.gba 덤프"
#   _ver0.3 롬은 쓰지 않음(2026-11-08~). 각 단계는 몇 번 다시 돌려도 결과가 같도록 만들어져 있음:
#     · 원래 빈 공간(FF)에 쓰는 데이터 → regions(rom) 구간을 먼저 FF로 지우고 새로 씀(줄어들어도 찌꺼기 없음)
#     · 기존 코드를 바꾸는 패치 → 각 프로그램에 적힌 "원래 값/새 값"으로 확인(둘 다 아니면 중단)
import os, time, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROMS = os.path.join(ROOT, "resource", "roms")
FINAL = os.path.join(ROMS, "The Legend of Zelda - Fushigi no Boushi(K)_ver1.1.gba")       # 최종(플레이용)

def read_final(path=FINAL):
    """최종 롬 읽기. 없으면 안내 후 중단"""
    if not os.path.exists(path):
        raise SystemExit("%s가 없습니다. %s를 먼저 생성하세요" % ((os.path.basename(path),) * 2))
    return bytearray(open(path, "rb").read())

def patch_u16(rom, name, patch, on=True):
    """patch = [(오프셋, 원래 u16, 새 u16)...]. on=True면 새 값, False면 원래 값으로 씀.
    현재 값이 원래/새 값 둘 다 아니면 중단(엉뚱한 곳 패치 방지)"""
    for off, old, new in patch:
        cur = struct.unpack_from("<H", rom, off)[0]
        assert cur in (old, new), "패치 불일치 [%s] @0x%X: %04X (기대 %04X 또는 %04X) — 중단" % (name, off, cur, old, new)
    for off, old, new in patch:
        struct.pack_into("<H", rom, off, new if on else old)
    print("  %s: %s" % ("버그픽스" if on else "원상복구", name))

def run(name, regions, apply, src=None, dst=FINAL):
    """src(기본 dst) 롬 읽기 → regions(rom) 구간 FF로 지움 → apply(rom) → dst 덤프"""
    src = src or dst
    print("[%s] 롬 읽기: %s" % (name, os.path.basename(src)))
    rom = read_final(src)
    for s, e in regions(rom):
        rom[s:e] = b"\xFF" * (e - s)
    apply(rom)
    tmp = dst + ".tmp"                 # 임시파일에 다 쓴 뒤 교체(도중 실패해도 기존 롬 안 깨짐)
    with open(tmp, "wb") as f:
        f.write(rom)
    for i in range(10):                # 백신·인덱서가 방금 쓴 파일을 잠깐 잡는 경우(WinError 5) 재시도
        try:
            os.replace(tmp, dst); break
        except PermissionError:
            if i == 9:
                raise SystemExit("덤프 실패: %s 이(가) 다른 프로그램(에뮬레이터 등)에서 열려 있음" % os.path.basename(dst))
            time.sleep(0.5)
    print("[%s] 덤프: %s" % (name, os.path.basename(dst)))
    return rom
