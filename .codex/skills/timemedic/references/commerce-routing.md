# 몸의 발명사 조건부 쇼핑·쿠팡 제휴 라우팅

## 목적

건강·의학 역사 영상의 신뢰를 해치지 않으면서 실제 관련 상품이 있는 편만 쇼핑 수익화 후보로 보낸다. 상품을 찾았다는 이유로 본편 대본을 광고로 바꾸거나 모든 편에 링크를 붙이지 않는다.

## 세 가지 판정

- `eligible`: 주제와 직접 관련된 판매 상품이 있고 정확한 상품·옵션·판매자·현재 가격·재고·배송·주장을 검증할 수 있다.
- `review_required`: 관련성은 있으나 의약품·응급의료·효능 표현·연령·플랫폼 정책 또는 상품 동일성 검토가 더 필요하다.
- `not_eligible`: 억지 연관, 의료 오해 위험, 검증 불가 상품, 품절·옵션 불명, 본편 신뢰를 해치는 경우.

## 실행 순서

1. `15_packaging_release`에서 본편 완성도를 먼저 잠근다.
2. `$run-coupang-partners-shorts-lab`으로 후보 상품을 검증한다. 박카스·까스활명수처럼 영상 주제 자체가 상품이어도 정확한 판매 옵션과 현재 표시 정보는 별도 확인한다.
3. `official`, `marketplace_visible`, `review_pattern`, `inferred`, `forbidden` 주장을 분리한다.
4. 정확한 상품 URL, SKU/옵션, 판매자, 가격, 재고, 배송, 확인 시각, source_ids를 저장한다.
5. 쿠팡 파트너스 포털에서 해당 미디어 등록 상태와 최신 고지 문구·운영정책을 게시 직전에 다시 확인한다.
6. YouTube Studio에서 대상 채널의 Shopping 자격과 해당 상품 태그 가능 여부를 확인한다. 자격이 없거나 상품이 없으면 외부 제휴 링크 경로만 검토한다.
7. 제휴 관계가 있으면 YouTube `유료 프로모션` 항목을 사실대로 체크하고 설명 첫부분에 쿠팡 제휴 고지를 둔다.
8. 정확한 상품·링크·고지·플랫폼·채널을 사람이 승인한 뒤 한 번만 게시하고 canonical URL과 idempotency key를 남긴다.

## 기본 배치

- 설명 첫부분: `[광고]`와 최신 공식 쿠팡 제휴 고지. AI 재현 고지보다 제휴 고지가 먼저 보여야 한다.
- 그다음: 한 줄짜리 정확한 상품명·옵션과 승인된 제휴 링크.
- 본문: 역사·의학 이야기 설명과 AI 재현·의료 안전 고지.
- 고정 댓글: 플랫폼이 허용하고 별도 승인된 경우에만 같은 고지와 링크를 반복한다.
- YouTube Shopping 태그: 채널 자격, 판매자, 상품 일치, 수수료 조건을 Studio에서 실제 확인한 경우만 사용한다.

## 금지

- 상품이 있다는 이유로 `이 제품이 치료한다`, `살린다`, `무조건 효과`, `최저가`, `1위`를 근거 없이 쓰지 않는다.
- 직접 써보지 않았는데 사용 후기처럼 말하지 않는다.
- 가격·재고·할인·배송을 과거 캡처로 재사용하지 않는다.
- 구급상황의 역사 영상에 일반 소비재를 억지로 끼우거나 시청자의 불안을 이용해 구매를 강요하지 않는다.
- 자동 클릭·자동 구매·쿠키 삽입·가짜 리뷰·가짜 수익·중복 게시를 하지 않는다.

## `commerce_route` 계약

```json
{
  "status": "eligible|review_required|not_eligible",
  "reason": "주제와 상품의 직접 관련성 및 의료 안전 판단",
  "product": {
    "url": null,
    "sku_or_option": null,
    "seller": null,
    "price": null,
    "stock": null,
    "shipping": null,
    "checked_at": null
  },
  "source_ids": [],
  "affiliate_link": null,
  "disclosure_text": null,
  "youtube_paid_promotion": null,
  "youtube_shopping_tag": "unchecked|eligible|unavailable",
  "exact_package_approved": false,
  "idempotency_key": null,
  "publish_blockers": []
}
```

`exact_package_approved=false`면 본편을 비제휴 상태로 게시할 수는 있어도 링크·상품 태그는 넣지 않는다.
