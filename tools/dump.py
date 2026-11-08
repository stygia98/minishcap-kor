# 롬 개조 덤프: [2] 이름입력 한글개조 → [3] fix/ 4종 → [4] R버튼 캡션 을 resource/roms/...(K)_ver1.1.gba 에 적용
#   (각 프로그램 = 롬 읽기 → 자기 영역을 _ver0.3 값으로 되돌림 → 적용 → 덤프. 몇 번 돌려도 결과 같음)
#   대사 과정(별도): ① make_script.py (zip 3개 → script.json·review.html) → ② review.html 수정·JSON 내보내기
#                    → ③ update_k10.py (script.json ko → k1.0 zip) → ④ insert_kr.py (k1.0 zip → (K)_ver1.1.gba) → ⑤ rompatcher/build.py
#   이 파일은 이름개조·버그픽스·엔딩롤·R버튼 캡션을 바꿨을 때(또는 (K)_ver1.1.gba를 새로 만들 때 ④ 다음에) 실행
#   단독 실행: python tools/kor_char_sys/build_kor_char_sys.py / tools/fix/rcaption.py
#              python tools/fix/save_checksum.py / figurine_zero.py / staffroll.py / dhc_whirlwind.py / vaati3_fall.py / darknut_timer.py / mazaal_grab.py
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("", "kor_char_sys", "fix"):
    sys.path.insert(0, os.path.join(HERE, d))
import rom_stage
import build_kor_char_sys
import save_checksum, figurine_zero, staffroll, dhc_whirlwind, vaati3_fall, darknut_timer, mazaal_grab
import rcaption

build_kor_char_sys.main()
for fix in (save_checksum, figurine_zero, staffroll, dhc_whirlwind, vaati3_fall, darknut_timer, mazaal_grab):
    fix.main()
rcaption.main()
print("완료:", rom_stage.FINAL)
