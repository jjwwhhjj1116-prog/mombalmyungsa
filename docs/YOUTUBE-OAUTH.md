# 몸의 발명사 YouTube OAuth 연결

## 채널 하드락

- 공개 채널명: `몸의 발명사`
- 허용 channel ID: `UCYqdIlpFlB6uh_cpIYgo85g`
- 전용 실행 파일: `scripts/youtube_upload_body_invention.py`
- 다른 채널 토큰 탐색, 첫 토큰 자동 선택, token fallback, 채널명만 비교하는 검사는 금지한다.

업로드 대상은 OAuth 동의 때 선택한 YouTube 채널이 결정한다. 몸의 발명사 전용 토큰을 별도 발급하고, 파일을 읽기 전에 `channels.list(mine=true)`가 정확한 channel ID 하나만 반환하는지 검사한다.

## 비밀 파일

아래 파일은 `.gitignore`의 `.private/` 규칙으로 추적하지 않는다.

```text
.private/youtube/body-invention-oauth-client.json
.private/youtube/body-invention-token.json
.private/youtube/body-invention-upload-ledger.jsonl
```

고대유물 또는 테스트 채널의 `client_secrets.json`, `token.json`을 복사·이름 변경·fallback으로 사용하지 않는다.

## 최초 연결

1. Google Cloud 프로젝트에서 YouTube Data API v3를 사용 설정한다.
2. OAuth 대상이 `테스트 중`이면 몸의 발명사 채널을 관리하는 Google 계정을 테스트 사용자로 추가한다.
3. 데스크톱 앱 OAuth 클라이언트를 `몸의 발명사 자동업로더`라는 별도 이름으로 만든다.
4. 내려받은 JSON을 `.private/youtube/body-invention-oauth-client.json`으로 저장한다.
5. `python scripts/youtube_upload_body_invention.py --auth`를 실행한다.
6. 브라우저에서 몸의 발명사 채널을 선택해 동의한다.
7. 출력 channel ID가 `UCYqdIlpFlB6uh_cpIYgo85g`인지 확인한다.

OAuth 앱이 `테스트 중`이면 YouTube 권한의 refresh token이 7일 뒤 만료될 수 있다. 장기 자동화 전에는 앱 게시·검증 상태를 완료한다.

## 확인·점검·비공개 업로드

```powershell
python scripts/youtube_upload_body_invention.py --whoami
python scripts/youtube_upload_body_invention.py --package episodes/<episode>/packaging/<package>.json
python scripts/youtube_upload_body_invention.py --package episodes/<episode>/packaging/<package>.json --run
```

`--package`만 쓰면 업로드하지 않는다. `--run`도 항상 비공개 업로드만 수행한다. 업로드 직후 실제 `snippet.channelId`를 다시 확인하고 전용 비공개 원장에 idempotency key를 기록한다.

프로젝트가 YouTube API 감사를 통과하지 않았다면 API 업로드가 비공개로 제한될 수 있다. 이 경우 감사 완료 전에는 공개 예약을 성공으로 기록하지 않는다.
