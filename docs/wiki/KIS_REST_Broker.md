# KIS REST Broker

한국투자증권 Open Trading REST 기반 브로커 구현.

## 특징
- REAL / VTS 완전 분리
- Token 발급 + 캐싱 (cache/kis_token.json)
- Content-Type 정책 엄격 준수
- 실전 주문 보호 ENABLE_REAL_ORDER
- 오류 메시지 출력 강화

코드 위치:
```
src/brokers/kis_broker.py
```
