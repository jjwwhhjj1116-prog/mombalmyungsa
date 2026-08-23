# 의미 결합형 사운드 설계

## 원칙

사운드는 장면을 장식하지 않고 인과를 들려준다. 모든 소리는 다음 연결을 가진다.

```text
발화 문구 → TTS 단어 타임코드 → 화면 사건 → 사운드 큐 → 믹스 버스 → 인과 목적
```

화면 사건과 무관한 효과음, 매 컷마다 반복되는 우시, 분위기만 큰 영화 예고편 음악은 금지한다. 중요한 시각 타격은 소리를 2–3프레임 먼저 시작해 착지를 또렷하게 만든다.

## 네 개의 버스

1. `voice`: ElevenLabs clean TTS. 생성 영상에 대사나 내레이션을 굽지 않는다.
2. `diegetic`: 물, 고무장갑, 금속 대야, 종이, 문 여닫힘처럼 장면 안에서 실제로 날 소리.
3. `editorial`: 우시, 임팩트, 리버스 라이저, 팝, 카운터 틱처럼 의미 전환을 강조하는 소리.
4. `music`: 감정의 바닥만 만든다. 내레이션과 증거 수치를 덮지 않게 자동 덕킹한다.

## 생성 영상의 네이티브 오디오 정책

- `generated_native_if_clean_else_edit`: 물·바람·공간음처럼 장면에 정확히 맞고 깨끗할 때만 생성 영상 오디오를 쓴다. 불일치·잡음·가짜 대사가 있으면 클립을 음소거하고 편집 SFX로 교체한다.
- `edit_primary`: 장갑 스냅, 종이 선 긋기, 숫자 틱, 반전 임팩트처럼 프레임 정합이 중요한 소리는 편집에서 넣는다.
- `intentional_silence`: 딜레마, 질문 전환 직전처럼 침묵 자체가 의미일 때 음악과 환경음을 짧게 비운다.

한 클립의 생성 오디오가 좋더라도 다음 클립과 공간감·음량이 이어지지 않으면 사용하지 않는다. 생성 영상의 인물 대사는 타임메딕 내레이션과 충돌하므로 기본적으로 금지한다.

### `native_audio_plan` 규격

Omni 생성 단위와 각 서브샷에는 화면에 실제로 보이는 사건만 소리로 요구한다.

```json
{
  "subshot_id": "V01-B",
  "visible_event": "금속 뚜껑이 회전해 병목에서 분리된다",
  "requested_native_audio": ["short metal cap twist", "small glass neck click"],
  "forbidden_audio": ["speech", "narration", "music", "cinematic boom", "unseen crowd"],
  "harvest_policy": "keep_if_frame_locked_else_replace",
  "sync_tolerance_frames": 2,
  "continuity_bed": "same quiet pharmacy refrigerator room tone"
}
```

- `visible_event`가 없으면 네이티브 효과음을 요구하지 않는다.
- 수확 시 소리 시작점이 화면 사건에서 ±2프레임을 벗어나거나 가짜 대사·음악·잘못된 공간음이 섞이면 `mute_and_replace`다.
- 네이티브 오디오를 살릴 때도 clean TTS가 최상위다. 원본 음량을 자동 정규화하고 TTS 구간에서 덕킹한다.
- 컷이 바뀌어도 같은 공간이면 6–12프레임 크로스페이드로 room tone을 이어 붙인다. 공간이 바뀌면 보이는 문·벽 통과·매치컷 사건에 맞춰 전환한다.
- 한 생성 클립에서 좋은 물체음만 따로 수확할 수 있다. 영상 구간과 오디오 구간이 반드시 같을 필요는 없지만, 최종 배치는 화면 사건에 다시 프레임 정합해야 한다.

## 큐 선택

- 손 씻기·대야·고무: 낮은 볼륨의 다이에제틱 폴리.
- 손상·균열: 짧고 마른 질감. 공포 영화식 뼈 부러지는 소리는 금지한다.
- 반복: 같은 소리를 키우지 말고 틱 간격, 필터, 음높이를 단계적으로 좁힌다.
- 딜레마: 좌우 손실이 착지할 때 각각 한 번, 마지막에는 6–12프레임의 의도적 정적.
- 질문 전환: 짧은 리버스 라이저 뒤 방향이 바뀌는 순간 한 번의 임팩트.
- 손그림 선·형광펜: 선 끝점과 동기화한 연필·종이 마찰음.
- 숫자 증거: 숫자 변화에 부드러운 틱, 최종값에서만 낮은 확인음.
- 결말·루프: 따뜻한 해소음의 꼬리를 첫 장면의 공간음과 겹쳐 반복을 숨긴다.

## `sound_events[]` 규격

```json
{
  "sound_id": "snd-11b",
  "beat_id": 11,
  "trigger_phrase": "사람을 살리는 질문부터 뒤집습니다",
  "kind": "editorial",
  "asset_key": "reverse_whoosh_impact",
  "source_policy": "edit_primary",
  "sync": "pre_roll_to_phrase",
  "lead_frames": 3,
  "gain_db": -10,
  "duck_music_db": -6,
  "duration_policy": "one_shot",
  "causal_purpose": "질문의 방향이 뒤집히는 순간을 청각적으로 착지시킨다"
}
```

- `trigger_phrase`는 해당 비트 내레이션에 글자 그대로 있어야 한다.
- 실제 시간은 TTS 생성 후 단어 정렬에서 계산한다. 그 전에는 `pending_tts_word_alignment`로 둔다.
- `asset_key`는 라이브러리 키다. 라이선스와 파일 존재 여부를 별도로 검수한다.
- 에피소드당 보통 8–18개만 쓴다. 소리가 없는 샷도 의도적인 선택이다.

## 최종 믹스와 검수

- 보이스를 먼저 고정하고 음악·환경음·효과음을 그 아래 배치한다.
- 효과음 타격 때 음악을 대략 4–8dB 낮추고, 내레이션 중에는 음악을 지속적으로 덕킹한다.
- 클리핑, 갑작스러운 공간음 변화, 좌우 치우침, 생성 영상의 가짜 말소리를 검사한다.
- 휴대폰 스피커와 이어폰에서 모두 확인한다.
- 최종 출력은 `sound-timeline.json`과 `sound-cue-sheet.md`로 남긴다.
- 최종 출력에 `native-audio-audit.json`도 남기고 각 원본의 `keep`, `mute`, `replace`, `harvest_window`, `sync_error_frames`, `reject_reason`을 기록한다.
