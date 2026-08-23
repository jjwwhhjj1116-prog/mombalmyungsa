# 몸의 발명사 보이스와 연기

## 기본 경로 — ElevenLabs 고정 보이스

- 몸의 발명사 기본 화자는 ElevenLabs voice ID `wTGzPmtwk7nDNybbk0OL`로 고정한다. 프로젝트 표시명은 `오늘을 만든 이름들_역사해설_V3`일 수 있지만 자동화는 이름이 아니라 voice ID를 기준으로 확인한다.
- 합성 model ID는 `eleven_multilingual_v2`로 고정한다. ElevenLabs UI 표시는 `Eleven Multilingual v2`다.
- 설정은 `speed 1.05`, `stability 0.40`, `similarity_boost 0.85`, `style 0.50`, `use_speaker_boost true`로 고정한다.
- 다른 voice ID, Typecast, Eleven v3 또는 자동 추천 모델로 조용히 대체하지 않는다. 보이스나 모델을 바꾸려면 사용자의 새 명시 승인이 필요하다.
- 대본 전체를 합성하기 전에 훅, 질문, 딜레마, 중간 시그니처, 마지막 시그니처로 짧은 오디션을 만들 수 있다. 오디션도 같은 voice ID·모델·설정을 사용한다.
- 합성본은 처음부터 끝까지 사람이 듣는다. 어색한 문장은 발음 표기로 덮지 말고 문장 자체를 먼저 자연스럽게 고친다.
- 최종 음성에서 긴 무음만 줄인다. 질문 전환, 반전, 결말에 필요한 호흡까지 없애지 않는다.
- 무음 정리를 끝낸 파일의 실제 길이와 문장 타임코드를 영상·자막·카메라·오버레이의 유일한 시간축으로 잠근다.
- 수익화 채널에는 해당 ElevenLabs 구독의 상업 이용 조건과 생성 기록을 확인한다.

## Voice Design

```text
Native Korean. Male, 38–45. Excellent studio quality.
Persona: charismatic medical-history storyteller. Emotion: curious, urgent, warm.
A naturally resonant mid-low voice with crisp Seoul-standard Korean diction and clear pronunciation of medical terms. He speaks as if sharing an unbelievable true story with a small audience, never as a formal news announcer. The delivery begins intimate and curious, becomes faster and more pressurized as the problem repeats, lands rhetorical questions cleanly, then leaves a short charged silence before the reversal. The solution is delivered with precise conviction, and the final historical consequence with warm wonder. Energetic and highly immersive without shouting, caricature, theatrical imitation, or excessive vibrato.
```

Voice Design은 age, gender, accent, quality, persona, emotion, timbre, pacing, delivery를 구체적으로 적는다. 생성된 세 후보 중 의료 용어 자음, 질문 억양, 낮은 결말이 모두 되는 후보만 저장한다.

## ElevenLabs 입력 규칙

- 고정 모델이 `eleven_multilingual_v2`이므로 Eleven v3 전용 오디오 태그를 입력하지 않는다.
- SSML break나 읽힐 수 있는 연기 지시문 대신 줄바꿈, 쉼표, 말줄임표로 정적을 만든다.
- 숫자·기호는 단위에 맞춰 발음대로 적는다: `삼천 명`, `천팔백구십칠년`, `천구백십년대`, `육십 종`, `사점오삼 초`, `십칠 퍼센트`.
- TTS 입력에는 발음용 한글 `narration`만 넣고, 영상 자막은 같은 사실값의 숫자형 `caption`을 사용한다. `1897년`을 TTS에 그대로 보내거나 `천팔백구십칠년`을 화면 자막에 노출하지 않는다.
- 전체를 `훅 / 악화 / 딜레마 / 반전 / 결과`로 나누고 이전·다음 문맥을 보존한다.

## 건축·과학 사전형 전달 리듬

- 특정 화자의 음색·고유 억양·말버릇은 복제하지 않고 다음 고수준 문법만 사용한다.
- 한 문장을 1.4–3.2초 안에 이해할 수 있도록 짧고 단정하게 쓴다.
- 평소에는 빠르고 건조하게 설명하고, 놀라운 사실을 과장된 감탄 대신 낮은 단정으로 착지시킨다.
- 원인과 결과는 같은 호흡으로 묶고, 새 원인이 시작되면 새 문장으로 끊는다.
- 문제 누적 구간은 문장마다 속도와 압박을 조금씩 올린다.
- 양쪽 손실을 같은 리듬으로 읽은 뒤 짧게 숨을 들이마시고, `여러분, 이거 정말 미치고 팔짝 뛸 노릇 아니겠습니까?`는 답답함이 터지는 친근한 반문으로 읽는다. 고함이나 희극 연기로 과장하지 않는다.
- 질문 전환 직전 180–320밀리초의 체감 정적을 만들고 `그래서, 사람을 살리는 질문부터 뒤집습니다.`는 오히려 반 박자 느리게 읽는다.
- 수치·치수·연도는 속도를 낮춰 자음을 분명히 하고, `몸을 살린 생각의 전환, [대상]은/는 이렇게 탄생했습니다.`는 웅장함보다 낮고 따뜻한 확신으로 끝낸다.
- TTS는 문장별 감정 단위를 설계하되, 음색과 호흡이 튀지 않도록 `훅 / 악화 / 딜레마 / 반전 / 결과` 묶음으로 생성한다.

## 연속 합성 하드 게이트

- 승인 대본 전체를 한 번의 합성 요청으로 만드는 것이 기본이다.
- 공급자 길이 제한이나 명백한 재생성 비용 때문에 분할이 불가피할 때만 `훅 / 과거 문제 / 전환 / 결과` 같은 큰 이야기 구간 최대 3개로 나눈다.
- 문장별 또는 한두 문장별 파일을 여러 개 만든 뒤 이어 붙이지 않는다. 같은 사람도 새 요청마다 음색·속도·호흡이 달라져 다른 화자처럼 들릴 수 있기 때문이다.
- 모든 분할은 voice ID `wTGzPmtwk7nDNybbk0OL`, model ID `eleven_multilingual_v2`, speed `1.05`, stability `0.40`, similarity boost `0.85`, style `0.50`, speaker boost `true`와 같은 문맥 요약을 사용한다. 경계 전후를 실제로 듣고 음색·속도·호흡 점프가 하나라도 있으면 전체 또는 해당 큰 구간을 다시 합성한다.
- 영상·자막은 합성 전 예상 길이가 아니라 최종 연속 TTS와 강제정렬만 따른다.

## 사람이 들려주는 톤앤매너 계약

화자는 청자를 가르치는 강사가 아니다. 믿기 힘든 의학 역사를 먼저 발견한 뒤, 바로 옆 사람에게 “이거 한번 들어봐”라는 태도로 들려주는 사람이다.

1. `현장 관찰`: 눈앞에서 벌어지는 행동을 짧은 현재형으로 빠르게 붙인다.
2. `인간 반응`: “근데 잠깐만요”, “전기로?”, “이상하죠?”처럼 실제로 떠오를 반응을 한 번 끼운다.
3. `쉬운 비유`: 초등학생도 그릴 수 있는 상자·펌프·문·물길 같은 사물로 원리를 먼저 보여준다.
4. `전문 교정`: 비유 바로 뒤에 정확한 의학 문장을 붙여 비유가 사실을 왜곡하지 않게 한다.
5. `낮은 증거`: 연도·인물·숫자는 흥분하지 말고 속도를 낮춰 또렷하게 말한다.
6. `여운`: 결말은 교훈을 훈계하지 않고 첫 장면의 의미만 바꿔준다.

### 문장 리듬

- 한 문장은 보통 1.4–3.2초, 3–12어절로 쓴다. 핵심 질문과 짧은 단정은 더 짧아도 된다.
- `~니다`는 사실 착지에, `~죠`는 공감에, `~요`는 친밀한 설명에, `~다`는 반전 단정에 사용한다.
- 질문형은 호기심 구간에 집중하되 같은 질문 어미를 세 번 반복하지 않는다.
- “근데”, “잠깐만요”, “쉽게 말해” 같은 연결구는 한 편에서 각각 최대 두 번만 쓴다.
- `그런데 말이에요`, `그런데 말이예요`처럼 다음 사실 없이 호흡만 채우는 완충문은 금지한다.
- 감탄사를 세게 읽어 흥미를 만들지 않는다. 사건의 물리적 모순과 인과가 흥미를 만들게 한다.

### 금지 톤

- 교과서 요약: “심폐소생술의 역사에 대해 알아보겠습니다.”
- 뉴스 나열: “연구했습니다. 발견했습니다. 발표했습니다.”
- 가짜 친근함: 모든 문장을 `~죠`로 끝내기
- 빈 어그로: “충격적인 사실”, “소름 돋는 진실”, “레전드”
- 시청자 훈계: “그러니 여러분도 반드시 기억해야 합니다.”
- 특정 강사·성우·채널의 고유 억양, 말버릇, 고정 멘트를 복제하기

## 감정 곡선

1. 훅: 친밀한 호기심, 청자에게 말을 거는 느낌
2. 상식 반박: 마지막 단어에 짧고 선명한 착지
3. 문제 반복: 속도와 압박을 단계적으로 올림
4. 딜레마: 양쪽 손실을 같은 리듬으로 읽음
5. 막다름: 한숨을 남발하지 않고 한 번만 사용
6. 질문 전환: 볼륨보다 정적과 발음으로 강조
7. 행동: 정확하고 결연하게
8. 증거: 속도를 낮추고 숫자를 또렷하게
9. 결말: 따뜻한 경이, 과도한 웅장함 금지

특정 방송인·강사·성우의 음색, 고유 억양, 말버릇을 복제하지 않는다.
