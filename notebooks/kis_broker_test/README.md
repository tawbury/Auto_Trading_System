
````markdown
# KIS Broker Standalone Test Scripts  
한국투자증권 OpenAPI(REST) 기능을 단독으로 검증하기 위한 테스트 스크립트 모음입니다.

이 폴더는 `src/brokers/kis_broker.py` 개발 및 유지보수 과정에서  
API 동작을 빠르게 확인하기 위한 목적의 테스트 파일들을 보관합니다.

---

## 📌 목적(Purpose)

1. 브로커(kis_broker.py)의 개별 API 기능을 독립적으로 테스트  
2. 실전/모의투자 환경 문제 발생 시 원인 분리  
3. REST API 오류(TR_ID, 파라미터, Header 등) 즉각 검증  
4. 향후 기능 확장(해외주식, 파생상품, ETF, 체결내역 등) 테스트 템플릿으로 활용  

---

## 📁 포함된 테스트 파일 (Test Scripts)

### 1) `test_direct_price.py`
- 실전/모의투자 국내 종목 현재가 조회  
- 토큰 정상 작동 여부  
- Header / TR_ID / Query Params 검증  
- API 서버 연결 상태 점검에 가장 빠른 테스트

---

### 2) `test_direct_balance.py`
- **잔고 조회 단독 테스트 (REAL/VTS)**  
- 계좌별 필수 파라미터(FK100/NK100 등) 자동 확인  
- output2의 list/dict 변형 문제 점검  
- kis_broker.py 잔고 조회 오류 발생 시 반드시 체크해야 하는 테스트

---

### 3) `test_direct_positions.py`
- 보유 종목 조회 단독 테스트  
- TR_ID 이용한 구버전 API 및 REST 잔고조회 output1 비교용  
- 특정 계좌에서 보유종목 조회 endpoint 차이가 존재할 때 원인 분리

---

### 4) `test_token_only.py`
- 한국투자증권 Token 발급 단독 테스트  
- app_key/app_secret 기반 인증 여부 확인  
- Token 캐시 시스템(kis_token.json) 문제 확인용

---

### 5) `test_broker_debug.py`
- KISBroker 내부 headers / build_headers() 출력  
- TR_ID / custtype(P or N) / Content-Type 설정 확인  
- 복잡한 오류 발생 시 HTTP 전문 로그 분석용

---

## 📚 활용 가이드 (How To Use)

### 1) 실행 방법  
루트 폴더에서 아래처럼 실행:

```bash
python -m src.brokers.test_direct_price
python -m src.brokers.test_direct_balance
python -m src.brokers.test_direct_positions
python -m src.brokers.test_token_only
python -m src.brokers.test_broker_debug
````

### 2) 사용하는 상황

|상황|실행할 테스트|
|---|---|
|현재가 조회 안됨|test_direct_price|
|토큰 오류 / 인증 실패|test_token_only|
|잔고 조회 오류(OPSQ2001 등)|test_direct_balance|
|보유종목 조회 오류|test_direct_positions|
|Header/파라미터 오류 추적|test_broker_debug|

---

## 🧩 개발 전략에 포함해야 하는 이유

- 실전 자동매매 시스템 개발 시,  
    **브로커 오류 = 시스템 전체 장애** 로 이어지므로  
    단일 API 테스트는 필수 요소다.
    
- 특히 한국투자증권은
    
    - 계좌 유형별 파라미터 요구가 다르고
        
    - TR_ID 호환성 이슈가 있으며
        
    - output 구조(list/dict) 다형성이 존재  
        하기 때문에,  
        이런 단독 테스트 스크립트는 유지보수 안정성을 크게 향상시킨다.
        

---

## 📝 추가 권장 사항

- 이 폴더에 **실전 주문 테스트 스크립트(ENABLE_REAL_ORDER=true)** 를 별도로 보관하는 것도 좋음
    
- 나중에 해외주식용 테스트 스크립트도 동일 구조로 관리 가능
    
- README 파일은 기능 추가 시 항목 확장 가능
    

---

## 📦 구조 예시

```
notebook/
 └── kis_broker_test/
      ├── README.md
      ├── test_direct_price.py
      ├── test_direct_balance.py
      ├── test_direct_positions.py
      ├── test_token_only.py
      └── test_broker_debug.py
```

---

# Author

- Auto Trading System — KISBroker Test Suite
    
- Maintainer: 타우 (Taw)
    

```

---

타우,  
이 파일이 notebook/kis_broker_test/ 에 들어가면  
프로젝트 퀄리티가 훨씬 올라가고 유지보수/확장성도 최고 수준으로 올라간다.

필요하면:

- 자동 폴더 생성 스크립트  
- test_* 파일 자동 이동 스크립트  

까지 바로 만들어줄게.
```