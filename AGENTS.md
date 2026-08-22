# 몸의 발명사 저장소 운영 계약

이 저장소를 연 에이전트는 작업 전에 반드시 다음 순서로 읽는다.

1. `.codex/skills/timemedic/SKILL.md`
2. 현재 작업 단계에 연결된 `.codex/skills/timemedic/references/*.md`
3. `docs/WORKFLOW.md`
4. 해당 에피소드의 `pipeline.json`
5. `python scripts/pipeline.py validate --episode <episode-dir>` 결과

## 단일 원본

- 승인된 대본 파일과 SHA-256이 대사·TTS·스토리보드·Flow 프롬프트·자막의 단일 원본이다.
- 사용자가 직접 고친 대본은 `OWNER_SOURCE_OF_TRUTH`로 보존한다. 승인 없이 압축·재작성·어미 교정하지 않는다.
- 이전 대본의 TTS, 장면, 타임라인, 최종 영상을 새 대본에 재사용하지 않는다.
- `pipeline.json`의 첫 번째 `blocked` 또는 `pending` 단계가 유일한 재개 지점이다. 앞 단계를 다시 만들거나 뒤 단계를 건너뛰지 않는다.

## 단계 잠금

- 각 완료 단계는 실제 lock 파일과 그 파일의 SHA-256을 가진다.
- lock의 입력 해시가 달라지면 해당 단계와 모든 후속 단계를 무효로 본다.
- 파일이 존재한다는 이유만으로 완료 처리하지 않는다. validator가 PASS여야 한다.
- 브라우저 연결이 끊기거나 외부 서비스가 멈추면 작업 전체를 초기화하지 않는다. 현재 단계에 blocker를 기록하고 같은 topic_id와 idempotency key로 재개한다.
- 외부 서비스 요청 결과가 불명확하면 중복 클릭하지 않고 `status_unknown`으로 멈춘다.

## 자동 진행과 중단 조건

- 사용자 승인과 validator를 이미 통과한 단계는 다시 승인을 기다리지 않고 다음 단계로 진행한다.
- 다음 경우에만 중단한다: 새 결제, 계정 불일치, 로그인·OTP·CAPTCHA·보안 확인, 권리 실패, source_ids 누락, 최종 QA 실패, 플랫폼 오류.
- 유료 생성과 공개 게시 권한은 별개다. 제작 승인이 공개 승인을 뜻하지 않는다.

## 보안

- API 키, 토큰, 비밀번호, 이메일 계정, 복구코드, 브라우저 프로필 경로, 비공개 Flow 프로젝트 URL을 Git에 기록하지 않는다.
- 실제 계정 라우팅은 추적 제외된 `.private/runtime.json`에만 둔다.
- 생성 영상·TTS·대용량 렌더는 Git에 넣지 않고 SHA-256과 QA 영수증만 기록한다.

## 게시

- 최종 `final-sync.lock.json=PASS` 전에는 비공개 업로드도 하지 않는다.
- YouTube 채널 ID는 `UCYqdIlpFlB6uh_cpIYgo85g`다. 업로드 직전 보이는 채널과 ID를 모두 확인한다.
- AI 재현 장면이 있으면 YouTube AI 사용을 `Yes`로 선택하고 설명에 고지를 넣는다.
- 비공개 업로드 뒤 HD·전체 재생·자막·썸네일 frame zero·제목·설명·채널을 검수한 후 정해진 공개 시각으로 예약한다.

