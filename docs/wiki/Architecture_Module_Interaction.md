# Architecture – Module Interaction

## 시그널 → 주문 흐름

Strategy → Engine → Broker → KIS API → Fill → Sheets 업데이트

## 주문 → 리스크 검증 흐름

Sheets → Engine → Rules → Broker → Execution → Sheets 반영
