# [④] 번역 덤프: rom_script_cut(k1.1).zip 의 대사 전체(K 항목)와 블록8 지명 치환표를 (K)_ver1.1.gba 에 삽입
#   python tools/insert_kr.py [롬]   (기본: 최종본 (K)_ver1.1.gba 를 읽어 그 파일에 씀. 없으면 안내 후 중단, _ver0.3 안 씀)
#   대사 영역·지명표만 바꾸고 이름개조·버그픽스·R버튼(dump.py)은 그대로 둠
#   순서: 롬 읽기 → k1.1 zip 읽기 → tbl 2개(kor-table·kor-area) 읽기(지명 치환표) → 덤프
#   k1.1 zip 은 script.json 에서 tools/update_k.py 로 만듦(ko 검사도 그쪽에서). 이 단계는 script.json 을 안 읽음
#   대사 영역 0xE60000~0xEAFFFF: 먼저 전부 FF로 지우고 씀(320KB 넘치면 중단)
import os, sys, struct, zipfile
sys.path.insert(0, os.path.dirname(__file__))
import mc_codec as mc
import rom_stage

ROOT = rom_stage.ROOT
K10  = os.path.join(ROOT, "resource", "script-kor", "rom_script_cut(k1.1).zip")
KTBL = os.path.join(ROOT, "resource", "script-kor", "kor-table.tbl")
ATBL = os.path.join(ROOT, "resource", "script-kor", "kor-area.tbl")
TEXT_BASE = 0xE60000               # 대사 마스터 디렉토리(0x108ED8 언어0 포인터가 가리킴)
TEXT_END = 0xEB0000                # 대사 영역 끝(사용자 지정 2026-11-08, 320KB — 원본 약 286KB라 충분). 뒤는 미사용

# 블록8 지명 글자 치환표 (J판 방식 복원)
#   지명 표시 모드(텍스트 상태 bit5-6 == 1)에서 글자마다 0x805F7E0 호출:
#     언어(0x2000007)==0 이면 치환표(리터럴 0x5F804 → 원본 K 0xE4F000, u16 글자코드, 0 종료)를 검색해
#     i번째에서 찾으면 지명 폰트 page8(0xE58000)의 i번 글리프, 못 찾으면 (코드 & 0xFF)번 글리프
#   원본 K해킹은 표가 엉터리(글리프와 무관한 코드)라 지명을 0F 4F XX(=0x18XX → 못 찾음 → XX번)로 직접 지정했음
#   → 표를 kor-area.tbl 글리프 순서의 "일반 한글 코드"로 다시 채우면 블록8 지명을 평범한 한글로 쓸 수 있음
#     (기존 0F 4F XX 지명도 예비 경로로 그대로 표시됨)
#   글자코드 = 디코더 값: 1바이트 b → 0x100|b, 0B~0E xx → ((b&7)+1)<<8|xx, 0F xx(<30) → 0x200|xx,
#              0F 3x → 0x300|x, 0F 4n xx → (9+n)<<8|xx
AREA_TABLE_LIT = 0x5F804           # 치환표 주소 리터럴(롬 전체에서 이 한 곳만 참조)
AREA_TABLE_OLD = 0xE4F000          # 원본 K해킹의 표(엉터리) — 최종본에서는 FF로 지움
AREA_TABLE_OLD_END = 0xE50000
AREA_TABLE_OFF = 0xE57C00          # 새 표 자리(_ver0.3 FF), 사용자 지정 2026-11-08
AREA_TABLE_END = 0xE58000          # 뒤는 지명 폰트 page8 글리프

def area_chars():
    """kor-area.tbl -> 글리프 순서 글자 목록(인덱스 = 글리프 번호)"""
    out = []
    for line in open(ATBL, encoding="cp949").read().splitlines():
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

AREA_OLD_CODES = [0xFFFF, 0x021A, 0x0210]   # 원본 K 옛 표 앞 3칸(●·◎ 는 한글 테이블에 없어 이 값 유지)

def area_table(rom):
    enc = mc.load_tbl(KTBL)[4]
    assert struct.unpack_from("<I", rom, AREA_TABLE_LIT)[0] in (0x8000000 + AREA_TABLE_OLD, 0x8000000 + AREA_TABLE_OFF), "치환표 포인터 불일치"
    old = AREA_OLD_CODES
    codes = []
    for i, ch in enumerate(area_chars()):
        try:
            codes.append(char_code(mc.encode(ch, enc)))
        except Exception:                       # ●·◎ 등 한글 테이블에 없는 기호 → 원본 K 표 값 유지
            codes.append(old[i] if i < len(old) else 0xFFFF)
    assert len(set(codes)) == len(codes), "치환표 코드 중복"
    data = struct.pack("<%dH" % (len(codes) + 1), *codes, 0)
    assert AREA_TABLE_OFF + len(data) <= AREA_TABLE_END
    assert rom[AREA_TABLE_OFF:AREA_TABLE_END] == b"\xff" * (AREA_TABLE_END - AREA_TABLE_OFF), "치환표 자리가 비어 있지 않음"
    rom[AREA_TABLE_OFF: AREA_TABLE_OFF + len(data)] = data
    struct.pack_into("<I", rom, AREA_TABLE_LIT, 0x8000000 + AREA_TABLE_OFF)
    print("  지명 치환표: %d글자 @0x%X (J판 방식, 옛 표 0x%X 지움)" % (len(codes), AREA_TABLE_OFF, AREA_TABLE_OLD))

def regions(rom):
    """적용 전 FF로 지우는 구간: 대사 영역 전체 + 지명 치환표 새 자리 + 옛 표(안 쓰므로 지움)
    (포인터 0x5F804 는 area_table 이 원래/새 값 확인 후 씀)"""
    return [(TEXT_BASE, TEXT_END), (AREA_TABLE_OFF, AREA_TABLE_END), (AREA_TABLE_OLD, AREA_TABLE_OLD_END)]

def apply(rom):
    with zipfile.ZipFile(K10) as z:
        region, master = z.read("K"), z.read("0")
    # zip 무결성: 마스터 = K 앞 320바이트, 블록 시작 16정렬, 80블록 파싱
    assert region[:320] == master and len(master) == 320, "k1.1 zip: 0 항목과 K 항목 앞부분이 다름"
    dirs = struct.unpack("<80I", master)
    assert all(d % 16 == 0 for d in dirs) and len(region) % 16 == 0, "k1.1 zip: 16바이트 정렬 아님"
    nmsg = sum(len(mc.parse_block(region[d:(dirs[i + 1] if i < 79 else len(region))])[1]) for i, d in enumerate(dirs))
    capacity = TEXT_END - TEXT_BASE
    print("  k1.1 zip: 80블록 %d메시지, 대사 %d바이트 / 용량 %d" % (nmsg, len(region), capacity))
    if len(region) > capacity:
        sys.exit("중단: 용량 초과(%d > %d). 스크립트 재배치 필요." % (len(region), capacity))
    rom[TEXT_BASE: TEXT_BASE + len(region)] = region   # 대사 영역은 regions 에서 이미 FF로 지워 둠
    area_table(rom)
    return rom

def main(src=None, dst=rom_stage.FINAL):
    return rom_stage.run("번역 덤프", regions, apply, src, dst)

if __name__ == "__main__":
    main(dst=sys.argv[1] if len(sys.argv) > 1 else rom_stage.FINAL)
