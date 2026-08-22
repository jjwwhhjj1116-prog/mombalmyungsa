# 중단·재개 계약

## 재개할 때

```powershell
python scripts/pipeline.py validate --episode episodes/<slug>
python scripts/pipeline.py status --episode episodes/<slug>
```

1. validator가 완료 단계의 lock 파일과 SHA-256을 다시 계산한다.
2. 첫 번째 `blocked` 또는 `pending` 단계를 `next_stage`로 선택한다.
3. 그 단계의 선행 lock만 입력으로 사용한다.
4. 이미 통과한 단계는 입력 해시가 바뀌지 않은 한 재생성하지 않는다.
5. 외부 서비스가 실패하면 같은 stage와 topic_id에 blocker를 기록한다.

## 무효화

- 승인 대본 한 글자라도 바뀌면 05단계의 새 revision을 만들고 06–15단계를 다시 만든다.
- 썸네일 배경이나 카피가 바뀌면 06 thumbnail lock과 첫 Flow 훅 단위, frame zero, 14–15단계를 다시 검수한다.
- 최종 TTS가 바뀌면 11–15단계 전체를 다시 만든다. 임시 정렬과 자막 타임라인은 재사용하지 않는다.
- Flow 원본 하나가 교체되면 해당 수확 구간과 영향을 받은 경계부터 10–15단계를 다시 검수한다.

## 실패 기록

blocker에는 다음을 남긴다.

```json
{
  "stage_id": "08_pilot_generation",
  "status": "blocked",
  "reason_code": "external_editor_unresponsive",
  "generation_submitted": false,
  "last_confirmed_state": "prompt_not_submitted",
  "safe_resume": "submit_first_pilot_once_after_account_and_settings_verification"
}
```

`blocked`는 전체 실패가 아니다. 비용과 중복 게시를 막고 정확한 단계에서 재개하기 위한 상태다.

## 금지

- 새 topic_id나 새 idempotency key로 같은 에피소드를 우회하지 않는다.
- 구버전 음성·영상이 폴더에 존재한다는 이유로 사용하지 않는다.
- 외부 생성 결과가 불명확한 상태에서 버튼을 다시 누르지 않는다.
- 최종 QA가 없는 파일을 임시 업로드하지 않는다.

