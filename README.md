# 몸의 발명사 제작 자동화

몸의 발명사 쇼츠를 **주제 선정부터 근거 검증, 대본, 디오라마 Flow 영상, TTS, 강제정렬, VOK 편집, 최종 QA, YouTube 업로드와 공개 확인까지** 단계 잠금 방식으로 운영하는 저장소다.

이 저장소의 목적은 브라우저나 컴퓨터가 끊겨도 작업이 초기화되지 않게 만드는 것이다. 모든 에피소드는 마지막으로 검증된 lock 다음 단계에서 이어진다.

## 시작 순서

```powershell
.\scripts\run-pipeline.ps1 validate
.\scripts\run-pipeline.ps1 status
```

상태 명령이 알려주는 `next_stage`만 수행한다. 단계가 끝나면 산출물과 SHA-256을 lock에 기록하고 다시 검증한다.

## 저장소 구조

```text
.codex/skills/timemedic/       몸의 발명사 전체 제작 스킬과 세부 레퍼런스
.github/workflows/validate.yml GitHub에 올라올 때 구조·해시 자동 검사
config/stages.json             00–15단계의 기계 판독 계약
config/topic-source-100.txt    사용자가 처음 제공한 100개 주제 원문
config/topic-catalog-100.json  100개 주제의 검증 전 구조화 카탈로그
config/50-day-two-video-schedule.json  번호 순서의 하루 2편 스케줄
docs/WORKFLOW.md               사람이 읽는 전체 워크플로
docs/RESUME.md                 중단·재개·무효화 규칙
episodes/<slug>/pipeline.json  에피소드별 현재 상태와 다음 단계
episodes/<slug>/locks/         완료 단계의 SHA-256 잠금
scripts/pipeline.py            상태·해시·선행 단계 검증기
```

## 운영 시간

- 오전편: 10:00 비공개 업로드, 11:00 공개 예약
- 오후편: 18:00 비공개 업로드, 19:00 공개 예약
- 일정이 지나도 미완성 영상을 올리지 않는다. 최종 동기화와 QA가 PASS인 영상만 다음 슬롯으로 넘긴다.
- GitHub Actions는 10:00·18:00 KST에 잠금과 재개점을 검사한다. 실제 Flow·ElevenLabs·YouTube 작업은 로그인된 로컬 Chrome이 필요한 Codex 자동화가 검사 결과를 읽고 수행한다.

## 현재 체크포인트

첫 이관 에피소드는 `까스활명수 V6`다. 사용자 승인 대본·문장별 스토리보드·`까스 / 없는 / 활명수` 썸네일 계약·Omni 생성 계획까지 잠겨 있고, 다음 단계는 `08_pilot_generation`이다. 구버전 TTS와 구버전 영상은 폐기 대상으로 명시되어 있다.

세부 규칙은 [전체 워크플로](docs/WORKFLOW.md), [재개 계약](docs/RESUME.md), [몸의 발명사 스킬](.codex/skills/timemedic/SKILL.md)을 따른다.
