# [엔딩롤] 엔딩 스태프롤에 "한글화" 페이지 1장 추가 (버그픽스 아님, 기능 추가)
#   python tools/fix/staffroll.py [롬]   (기본: 최종본 (K)_ver1.1.gba) — 이 수정만 단독 재덤프
#   페이지 문구("한글화 stygia")는 대사 블록2 #18(원래 미사용 빈 메시지)에 있음 → 대사 덤프(insert_kr)로 들어감
#   스태프롤 = 12바이트 엔트리 순서표 [동작u8, 폰트u16, -, 타이머u16, 텍스트u16, BG X u16, -u16] (tmc staffroll.c)
#     동작 0=대기 1=배경 2=텍스트 표시 3/6=정리 7=종료. 일본어 표 0x126FB4(71엔트리), 리터럴 0xA3468이 유일 참조
#   표 바로 뒤가 영어판 표라 제자리 확장 불가 → 빈 공간으로 복사하며
#   EXECUTIVE PRODUCER(텍스트 0x111=블록2 #17) 표시+대기 뒤에 블록2 #18(0x112) 표시+대기 삽입
#   원래 표(0x126FB4)는 그대로 두고 포인터만 새 표로 바꿈
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rom_stage

LIT = 0xA3468                      # 표 주소 리터럴
OLD = 0x126FB4                     # 원래 일본어 표
NEW = 0xE57800                     # 새 표 자리(_ver0.3 FF), 사용자 지정 2026-11-08 (이전 0xFFF000)
END = 0xE57C00                     # 뒤는 지명 치환표(insert_kr)
AFTER = 0x111                      # 이 텍스트 페이지 다음에 삽입
ADD = [(2, 1, 0, 300, 0x112, 0, 0), (0, 0, 0, 60, 0, 0, 0)]

def regions(rom):
    return [(NEW, END)]         # 새 표 자리(원래 FF) — 적용 전 FF로 지움

def apply(rom):
    assert struct.unpack_from("<I", rom, LIT)[0] in (0x8000000 + OLD, 0x8000000 + NEW), "스태프롤 표 포인터 불일치"
    ents, o = [], OLD
    while True:
        e = struct.unpack_from("<BHBHHHH", rom, o)
        ents.append(e)
        o += 12
        if e[0] == 7:
            break
    i = next(k for k, e in enumerate(ents) if e[0] == 2 and e[4] == AFTER)
    assert ents[i + 1][0] == 0, "삽입 위치 뒤가 대기 엔트리가 아님"
    ents[i + 2:i + 2] = ADD
    data = b"".join(struct.pack("<BHBHHHH", *e) for e in ents)
    assert NEW + len(data) <= END, "스태프롤 표가 자리(0x%X~0x%X)를 넘음" % (NEW, END)
    assert rom[NEW:NEW + len(data)] == b"\xff" * len(data), "스태프롤 새 표 자리가 비어 있지 않음"
    rom[NEW:NEW + len(data)] = data
    struct.pack_into("<I", rom, LIT, 0x8000000 + NEW)
    print("  스태프롤: 한글화 페이지 추가 (%d엔트리 @0x%X)" % (len(ents), NEW))
    return rom

def main(src=None, dst=rom_stage.FINAL):
    return rom_stage.run("엔딩롤", regions, apply, src, dst)

if __name__ == "__main__":
    main(dst=sys.argv[1] if len(sys.argv) > 1 else rom_stage.FINAL)
