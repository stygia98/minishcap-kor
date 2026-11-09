# 젤다의 전설 이상한 모자 — 한글화

GBA **젤다의 전설 이상한 모자**(ゼルダの伝説 ふしぎのぼうし, 일본판) 한글 패치입니다.

2009년 한글화(ver0.3)를 바탕으로, 일본어판 원문을 기준으로
**대사를 처음부터 다시 번역**하고 기존 한글판과 원작의 버그를 고쳤습니다.

## 주요 내용

- **대사 전면 재번역**: 일본어 원문 기준, 약 2,900개 대사
- **기존 한글판 문제 해결**: 제어문 누출(깨진 글자), 줄 잘림, 빈 대사창
- **이름 입력 한글 조합**: 두벌식으로 한글 이름 입력(받침·겹받침·복모음 지원)
- **그래픽**: R버튼 동작 캡션 다시 번역, 지명 표시를 일본어판 방식으로 변경
- **버그 수정**(원작 포함)
  - 세이브 파일이 손상된 것으로 잘못 판정되는 문제
  - 피규어를 다 모은 뒤 뽑기에서 없는 피규어가 나오는 문제
  - 암흑 하이랄 성 회오리 방에서 일부 에뮬레이터가 멈추는 문제
  - 최종 보스 3형태에서 팔에서 나올 때 필드 밖으로 끝없이 떨어지는 문제
  - 최종 보스 직전 의식 타이머가 대화 중 끝나면 게임이 멈추는 문제
  - 바람의 요새 보스(마자르) 손에 잡힌 채 조작할 수 없게 되는 문제

버전별 변경 사항은 [CHANGELOG.md](CHANGELOG.md)를 참고하세요.

## 패치 방법

1. [Releases](../../releases/latest)에서 `MinishCap_KoreanPatch_ver1.1.exe`를 받습니다(이전 버전 ver1.0·ver0.3도 [Releases](../../releases)에 있습니다).
2. 실행한 뒤 **[한글 패치]** 탭에서 일본어판 원본 롬을 고르고 **패치하기**를 누릅니다.
3. 한글판 롬(`…(K)_ver1.1.gba`)이 새로 만들어집니다. 원본 롬은 바뀌지 않습니다.

|                       | 크기 | CRC32      |
| --------------------- | ---- | ---------- |
| 필요한 원본(일본어판) | 16MB | `6CE771A5` |
| 패치 결과(ver1.1)     | 16MB | `7073540C` |

- CRC32가 다른 롬(미국판·유럽판·다른 패치를 적용한 롬)은 거부합니다.
- **[세이브 이름 수정]** 탭: `.sav` 파일의 플레이어 이름을 한글로 바꿀 수 있습니다.
- 세이브 호환: 일본판·유럽판 세이브는 그대로 쓸 수 있고, 미국판 세이브는 쓸 수 없습니다.

> 롬 파일은 이 저장소에서 제공하지 않습니다. 직접 소유한 게임에서 추출한 롬을 사용하세요.

## 개발 환경

Windows, Python 3 기준입니다.

```powershell
# 프로젝트 전용 패키지(tools/_vendor, git 제외)
pip install --target tools/_vendor keystone-engine unicorn ziglang pyinstaller
# 참고용 디컴파일 저장소(git 제외)
git clone --depth 1 https://github.com/zeldaret/tmc ref/tmc
```

롬은 `resource/roms/`에 둡니다(롬 파일은 git 제외).

- `1743 - The Legend of Zelda - Fushigi no Boushi(J).gba`: 일본어판 원본(CRC32 `6CE771A5`). 패치 생성(`make_patch`)·화자 분석에 사용
- `The Legend of Zelda - Fushigi no Boushi(K)_ver1.1.gba`: 덤프 대상. 처음에는 원본 롬에 패처 exe를 적용해 만듭니다(모든 도구가 이 파일을 읽고 씀)

### 작업 흐름

```powershell
python tools/script_review/make_script.py   # ① 대사 zip → work/script.json·review.html
#                                            ② work/review.html 에서 번역 수정 → JSON 내보내기
python tools/update_k.py                     # ③ script.json → rom_script_cut(k1.1).zip
python tools/insert_kr.py                    # ④ 대사를 롬에 덤프
python tools/dump.py                         #    롬 개조(이름 입력·버그 수정·R버튼 캡션)
python tools/rompatcher/build.py             # ⑤ 패치 exe 빌드
```

검사 도구:

```powershell
python tools/script_review/ctrl_census.py ko   # 제어 코드가 일본어 원문과 같은지
python tools/script_review/mc_width.py         # 한 줄이 대사창 폭을 넘는지
python tools/unicorn/test_vaati3_fall.py       # 롬 코드 수정 검증(unicorn 에뮬레이터, test_*.py 각각 실행)
```

자세한 구조와 리버싱 기록은 [CLAUDE.md](CLAUDE.md)에 있습니다.

## 폴더 구조

```
resource/       대사 블록(zip)·폰트 테이블·스크린샷 / roms(git 제외)
tools/          덤프·검수·롬 수정·패처 도구
  fix/          버그 수정 스크립트
  kor_char_sys/ 이름 입력 한글 조합(C 소스)
  rompatcher/   한글 패치 exe
  unicorn/      롬 코드 검증 테스트
work/           script.json(번역 원본)·review.html(검수 앱)·말투표
```

## Special Thanks

- [zeldaret/tmc](https://github.com/zeldaret/tmc): 이상한 모자 디컴파일(코드 분석 참고)

## 한글화

stygia

이 프로젝트는 팬 번역이며 Nintendo와 관련이 없습니다. 「젤다의 전설」은 Nintendo의 상표입니다.
