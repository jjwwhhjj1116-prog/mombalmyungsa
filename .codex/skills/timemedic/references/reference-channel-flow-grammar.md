# 몸의 발명사 레퍼런스 채널형 Flow 문법

## 목적

공개된 신비한 건축사전형 제작 튜토리얼에서 확인한 제작 원리를 몸의 발명사 전용 Flow Omni Flash 프롬프트로 변환한다. 특정 채널의 화면, 대사, 캐릭터, 편집 결과, 워터마크를 복제하지 않는다. 채택 대상은 고수준의 이야기·촬영·편집 문법뿐이다.

## 확인된 제작 원리

- 대본 초안을 사람이 말맛 있게 고친 뒤 최종 TTS를 먼저 확정한다.
- 긴 무음만 정리한 최종 TTS 길이와 문장 경계를 영상 설계의 유일한 시간축으로 쓴다.
- 대본을 2–3문장의 8초 멀티샷 생성 단위로 묶는다.
- Flow에는 `SHOT A/B/C`별 행동, 카메라 목적, 종료 앵커를 넣는다.
- 8초를 통째로 쓰지 않고 문장에 정확히 맞는 1–3초 구간만 수확한다.
- 컷은 문장 종료 프레임에서 넘기며 다음 문장의 결과를 먼저 보여주지 않는다.
- 최종 자막과 정확한 한글·숫자는 생성 모델이 아니라 후반 렌더러에서 합성한다.

근거가 되는 내부 분석은 다음 경로를 source ID로 보존한다.

- `outputs/body-invention/cpr-discovery/research/reference-workflow-analysis-6FYfDgr-EIo.md`
- `outputs/body-invention/cpr-discovery/research/reference-workflow-analysis-ObvCtB1ATnA.md`
- `references/flow-clean-info-production.md`
- `assets/omni-stage-pipeline.json`의 `benchmark_reference`

## 6비트 영상 문법

1. `현대 결과`: 승인 썸네일과 같은 첫 프레임에서 이미 작동 중인 결과를 보여준다.
2. `상식의 모순`: 익숙한 대상 안으로 매크로 진입해 왜 가능한지 묻는다.
3. `실패 누적`: 같은 문제가 반복되는 물리 행동을 와이드→미디엄→클로즈업으로 악화시킨다.
4. `막힘과 홀드`: 두 선택이 모두 실패한 직후 움직임을 잠깐 줄이고 핵심 대상에 6–10프레임 머문다.
5. `질문 전환`: 새 생각이 나오는 발화에 맞춰 카메라 축, 피사체 행동, 환경 반응을 동시에 바꾼다.
6. `현재 회수`: 해결 결과에서 첫 장면의 물체·손·계기판으로 매치컷해 의미를 닫는다.

## Flow 프롬프트 컴파일 계약

각 8초 생성 단위는 아래 순서를 모두 가진다.

```text
STYLE PREFIX: 몸의 발명사 9:16 무광 레진 의료박물관 디오라마.
SHOT A [정확한 초 구간]: 현재 문장의 시작 행동, 카메라 시작점, 종료 앵커.
SHOT B [정확한 초 구간]: 인과 과정, 피사체 행동, 카메라 이동, 환경 반응.
SHOT C [정확한 초 구간]: 질문·증거·반전 행동, 카메라 착지점, 짧은 홀드.
CONTINUITY IN: 이전 단위에서 이어받는 물체·방향·빛.
CONTINUITY OUT: 다음 단위로 넘기는 물체·방향·빛.
HARVEST: 각 sentence_id에서 건질 시작 행동과 완료 행동.
AVOID: 실사 피부, 정지 포즈, 무의미한 줌, 립싱크, 글자, 숫자, 로고, 고어, 모핑, 중복 팔다리, 다음 문장 스포일러.
```

`장면(scene)`과 `감정(emotion)`은 장식이 아니다. 긴박하면 피사체와 카메라가 빠르게 이동하고 목표에서 감속한다. 절망이면 움직임이 좁아지고 선택지 두 개를 같은 리듬으로 보여준다. 반전이면 발화 순간에 카메라 축과 행동이 함께 바뀐다.

## reference grammar lock

Flow 생성 전 다음 잠금을 만든다.

```json
{
  "schema_version": "timemedic.reference-grammar-lock.v1",
  "status": "PASS",
  "source_analysis_paths": [],
  "adopted_high_level_rules": [],
  "copied_specific_scene": false,
  "generation_unit_ids": [],
  "script_sha256": "64-hex",
  "storyboard_sha256": "64-hex",
  "lock_sha256": "64-hex"
}
```

잠금이 없거나 `copied_specific_scene=true`, 분석 출처가 비어 있음, 생성 단위가 비어 있음이면 유료 Flow 생성을 차단한다.

## TTS와 최종 합성

- 최종 영상 프레임 수는 `round(TTS 초 × fps)`다.
- 문장 장면은 해당 문장의 강제정렬 시작 프레임부터 종료 프레임까지만 소유한다.
- 자막 페이지는 포함된 첫 단어의 시작 시각부터 마지막 단어의 끝 시각까지만 보인다.
- 영상과 TTS 길이 차이는 최대 1프레임이다.
- 자막 블록 중심은 1080x1920 기준 `x=540`, `y=1200`이다.
- 본문 자막은 `Gmarket Sans Bold 100px`, 검정 외곽선 30px, 그림자다.
