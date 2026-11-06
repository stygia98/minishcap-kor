# K롬 전용 ROM 버그픽스 (J판 코드 기준 = K와 동일 오프셋). dump.py 마지막 단계에서 적용.
# 각 패치 = (오프셋, 기존 u16, 새 u16). 기존 바이트와 다르면 중단(엉뚱한 곳 패치 방지).
import struct

# [1] 세이브 상태 체크섬 0x0 오판 버그  (출처: ARHafer/TMC_Bug-Fix-and-Analysis)
#   ParseSaveFileStatus @0x7CF64, 'MCZ3' 케이스:
#     기존: (checksum1 + checksum2) == 0x10000  → checksum1=0,checksum2=0 세이브를 손상 오판
#     수정: (checksum1 + checksum2) & 0xFFFF == 0  ( = checksum2 == (u16)(-checksum1) )
#   0x7CF90 adds r0,r0,r1  (합, 유지)
#   0x7CF92 movs r1,#0x80  → lsls r0,r0,#16
#   0x7CF94 lsls r1,r1,#9  → lsrs r0,r0,#16   (r0 = 합 & 0xFFFF)
#   0x7CF98 cmp  r0,r1     → cmp  r0,#0
SAVE_CHECKSUM_ZERO = [
    (0x7CF92, 0x2180, 0x0400),
    (0x7CF94, 0x0249, 0x0C00),
    (0x7CF98, 0x4288, 0x2800),
]

# [5] 피규어 뽑기 "1개 0%" 버그 (J/U/E 공통 원본 버그, 2026-11-06)
#   지금 얻을 수 있는 피규어를 다 모으면(SHOP07_COMPLETE) 확률 0%인데, 최저 확률 보정
#   FigurineDevice_GetChanceBasedOffFigurineCount @0x88228 이 0%도 15/12/9/6%로 올림
#   → 당첨돼도 고를 피규어가 없어 무작위 번호(미출시 피규어 포함)가 나오고, 소지 표시만 되고
#     개수(figurineCount)는 안 늘어 컴플리트 메달을 영영 못 받음.
#   수정: 분기 4곳  movs r0,#0 / ldrsb r0,[r1,r0] / cmp r0,#N / bgt
#             →  ldrb r0,[r1] / subs r0,#1 / cmp r0,#N-1 / bhi
#   (0-1 = 부호 없는 큰 수 → 보정 건너뛰어 0% 유지 = 항상 가진 피규어 → 5루피. 1~N%는 기존과 동일)
FIGURINE_ZERO_CHANCE = [
    p for base, n in ((0x88238, 0x0E), (0x8824E, 0x0B), (0x88260, 0x08), (0x8826E, 0x05))
    for p in ((base, 0x2000, 0x7808), (base + 2, 0x5608, 0x3801),
              (base + 4, 0x2800 | n, 0x2800 | (n - 1)))
] + [(0x8823E, 0xDC1C, 0xD81C), (0x88254, 0xDC11, 0xD811), (0x88266, 0xDC08, 0xD808), (0x88274, 0xDC01, 0xD801)]

ALL = [("세이브 체크섬 0x0 손상 오판 수정", SAVE_CHECKSUM_ZERO),
       ("피규어 뽑기 0% 상태 최저 확률 보정 제외", FIGURINE_ZERO_CHANCE)]

# [2] 지명 글자 치환표 (J판 방식 복원)
#   지명 표시 모드(텍스트 상태 bit5-6 == 1)에서 글자마다 0x805F7E0 호출:
#     언어(0x2000007)==0 이면 치환표(리터럴 0x5F804 → K 0xE4F000, u16 글자코드, 0 종료)를 검색해
#     i번째에서 찾으면 지명 폰트 page8(0xE58000)의 i번 글리프, 못 찾으면 (코드 & 0xFF)번 글리프
#   원본 K해킹은 표가 엉터리(글리프와 무관한 코드)라 지명을 0F 4F XX(=0x18XX → 못 찾음 → XX번)로 직접 지정했음
#   → 표를 kor-area.tbl 글리프 순서의 "일반 한글 코드"로 다시 채우면 블록8 지명을 평범한 한글로 쓸 수 있음
#     (기존 0F 4F XX 지명도 예비 경로로 그대로 표시됨)
#   글자코드 = 디코더 값: 1바이트 b → 0x100|b, 0B~0E xx → ((b&7)+1)<<8|xx, 0F xx(<30) → 0x200|xx,
#              0F 3x → 0x300|x, 0F 4n xx → (9+n)<<8|xx
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AREA_TABLE_OFF = 0xE4F000
AREA_TABLE_END = 0xE50000          # 뒤는 이름개조 자모 글리프(page15)

def area_chars():
    """kor-area.tbl -> 글리프 순서 글자 목록(인덱스 = 글리프 번호)"""
    out = []
    for line in open(os.path.join(ROOT, "script-kor", "kor-area.tbl"), encoding="cp949").read().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            assert int(k[4:], 16) == len(out), "kor-area.tbl 순서 오류: " + line
            out.append(v)
    return out

def char_code(b):
    if len(b) == 1:
        return 0x100 | b[0]
    if len(b) == 2 and 0x0B <= b[0] <= 0x0E:
        return ((b[0] & 7) + 1) << 8 | b[1]
    if len(b) == 2 and b[0] == 0x0F:
        return 0x200 | b[1] if b[1] < 0x30 else 0x300 | (b[1] & 0xF)
    if len(b) == 3 and b[0] == 0x0F:
        return (9 + (b[1] & 0xF)) << 8 | b[2]
    raise ValueError(b.hex())

def area_table(rom):
    import mc_codec
    enc = mc_codec.load_tbl(os.path.join(ROOT, "script-kor", "kor-table.tbl"))[4]
    old = [struct.unpack_from("<H", rom, AREA_TABLE_OFF + 2 * i)[0] for i in range(3)]
    codes = []
    for i, ch in enumerate(area_chars()):
        try:
            codes.append(char_code(mc_codec.encode(ch, enc)))
        except Exception:                       # ●·◎ 등 한글 테이블에 없는 기호 → 원본 K 표 값 유지
            codes.append(old[i] if i < len(old) else 0xFFFF)
    assert len(set(codes)) == len(codes), "치환표 코드 중복"
    data = struct.pack("<%dH" % (len(codes) + 1), *codes, 0)
    assert AREA_TABLE_OFF + len(data) <= AREA_TABLE_END
    rom[AREA_TABLE_OFF: AREA_TABLE_OFF + len(data)] = data
    print("  지명 치환표: %d글자 @0x%X (J판 방식)" % (len(codes), AREA_TABLE_OFF))

# [3] 엔딩 스태프롤에 "한글화" 페이지 1장 추가
#   스태프롤 = 12바이트 엔트리 순서표 [동작u8, 폰트u16, -, 타이머u16, 텍스트u16, BG X u16, -u16] (tmc staffroll.c)
#     동작 0=대기 1=배경 2=텍스트 표시 3/6=정리 7=종료. 일본어 표 0x126FB4(71엔트리), 리터럴 0xA3468이 유일 참조
#   표 바로 뒤가 영어판 표라 제자리 확장 불가 → 빈 공간으로 복사하며
#   EXECUTIVE PRODUCER(텍스트 0x111=블록2 #17) 표시+대기 뒤에 블록2 #18(0x112, 원래 미사용 빈 메시지) 표시+대기 삽입
STAFF_LIT = 0xA3468
STAFF_OLD = 0x126FB4
STAFF_NEW = 0xFFF000               # ROM 끝 FF 영역(스크립트는 0xEAxxxx까지)
STAFF_AFTER = 0x111                # 이 텍스트 페이지 다음에 삽입
STAFF_ADD = [(2, 1, 0, 300, 0x112, 0, 0), (0, 0, 0, 60, 0, 0, 0)]

def staffroll_page(rom):
    assert struct.unpack_from("<I", rom, STAFF_LIT)[0] == 0x8000000 + STAFF_OLD, "스태프롤 표 포인터 불일치"
    ents, o = [], STAFF_OLD
    while True:
        e = struct.unpack_from("<BHBHHHH", rom, o)
        ents.append(e)
        o += 12
        if e[0] == 7:
            break
    i = next(k for k, e in enumerate(ents) if e[0] == 2 and e[4] == STAFF_AFTER)
    assert ents[i + 1][0] == 0, "삽입 위치 뒤가 대기 엔트리가 아님"
    ents[i + 2:i + 2] = STAFF_ADD
    data = b"".join(struct.pack("<BHBHHHH", *e) for e in ents)
    assert rom[STAFF_NEW:STAFF_NEW + len(data)] == b"\xff" * len(data), "스태프롤 새 표 자리가 비어 있지 않음"
    rom[STAFF_NEW:STAFF_NEW + len(data)] = data
    struct.pack_into("<I", rom, STAFF_LIT, 0x8000000 + STAFF_NEW)
    print("  스태프롤: 한글화 페이지 추가 (%d엔트리 @0x%X)" % (len(ents), STAFF_NEW))

# [4] 암흑하이랄성-회오리버그수정 (2026-11-05, 추측 기반 수정 — 크래시 실기 미확인)
#   ★ 원상복구: 아래 DHC_WHIRLWIND_FIX = False → python tools/dump.py (→ 필요 시 make_patch·exe 재빌드)
#     꺼 두면 0x426C~0x4273·0xE57F00~0xE57F23 이 원본(_base) 그대로 남음(다른 패치와 독립)
#     원본 바이트 0x426C: 89 00 51 58 C1 65 5A E0 / 수정 바이트: 00 4B 18 47 01 7F E5 08 + 스텁 36바이트
DHC_WHIRLWIND_FIX = True
# 암흑 하이랄 성 회오리 방 크래시(일부 에뮬레이터) 방지 — 원래 게임 버그
#   InitializeAnimation(0x08004260, tmc asm code_08003FC4.s): 프레임포인터 = gSpritePtrs[ent->spriteIndex].animations[animIdx]
#   애니메이션 표가 없는(NULL) 스프라이트(13~22·28·58·97: 플레이어 아이템 등)에 이 함수가 불리면
#   주소 animIdx*4(=0x38, BIOS 영역)를 읽음 → 실기는 BIOS 보호값(IRQ 직후 0xE55EC002)이 프레임포인터가 되고
#   그 주소(미사용 영역)의 오픈버스 값으로 우연히 넘어가지만, BIOS/오픈버스를 다르게 흉내 내는 에뮬레이터는
#   쓰레기 프레임 → 엉뚱한 타일 복사·점프로 멈춤/리셋. VBA-M 로그로 확인(2026-11-05):
#     Illegal word read from bios: 00000038 at 0800426c → Illegal byte read: e55ec002~5 at 0800432e~433e
#   수정: 0x426C~0x4273(lsls/ldr/str/b FrameZero)을 스텁으로 보내 표가 NULL이면 더미 프레임 사용
#     더미 = [프레임 0xFF(그래픽 갱신 안 함), 길이 0x7F, 0, 0x80(끝)] + [1](자기 자신으로 반복)
INITANIM_STUB = 0xE57F00           # 이름개조 코드(…0xE54537) 뒤 ~ 지명 폰트(0xE58000) 앞 빈 공간
INITANIM_OLD = bytes.fromhex("89005158c1655ae0")     # 0x426C: lsls r1,#2 / ldr r1,[r2,r1] / str r1,[r0,#0x5c] / b FrameZero

def initanim_stub():
    s = 0x8000000 + INITANIM_STUB
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

def initanim_fix(rom):
    assert bytes(rom[0x426C:0x4274]) == INITANIM_OLD, "InitializeAnimation 원본 불일치"
    code = initanim_stub()
    assert rom[INITANIM_STUB:INITANIM_STUB + len(code)] == b"\xff" * len(code), "스텁 자리가 비어 있지 않음"
    rom[INITANIM_STUB:INITANIM_STUB + len(code)] = code
    rom[0x426C:0x4274] = struct.pack("<HHI", 0x4B00, 0x4718, 0x8000000 + INITANIM_STUB + 1)   # ldr r3,[pc] / bx r3 / .word 스텁
    print("  버그픽스: 애니메이션 표 없는 스프라이트 BIOS 읽기 방지(암흑 하이랄 성 회오리 방 크래시)")

def apply(rom):
    """rom: bytearray. 모든 패치 적용(기존 바이트 검증 후)."""
    for name, patch in ALL:
        for off, old, new in patch:
            cur = struct.unpack_from("<H", rom, off)[0]
            assert cur == old, "패치 불일치 [%s] @0x%X: %04X (기대 %04X) — 중단" % (name, off, cur, old)
        for off, old, new in patch:
            struct.pack_into("<H", rom, off, new)
        print("  버그픽스:", name)
    assert struct.unpack_from("<I", rom, 0x5F804)[0] == 0x8000000 + AREA_TABLE_OFF, "치환표 포인터 불일치"
    area_table(rom)
    staffroll_page(rom)
    if DHC_WHIRLWIND_FIX:                       # 암흑하이랄성-회오리버그수정 (False 면 원상복구)
        initanim_fix(rom)
    else:
        print("  (암흑하이랄성-회오리버그수정 꺼짐 — 원본 코드 유지)")
    return rom

if __name__ == "__main__":
    import sys
    rom = bytearray(open(sys.argv[1], "rb").read())
    apply(rom)
    open(sys.argv[1], "wb").write(rom)
    print("패치 완료:", sys.argv[1])
