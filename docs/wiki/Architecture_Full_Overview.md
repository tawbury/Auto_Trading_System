# Architecture – Full Overview

전체 시스템 구성도 요약:

1. Broker Layer (KIS REST API)
2. Engine Layer (Execution Engine, Strategy Router)
3. Strategies Layer
4. Google Sheets DB (DT_Report, Position, Risk Monitor)
5. Risk Control Pipeline
6. Core(AppContext)
7. Cache(Token, Temp Data)

각 Layer는 독립적이며 AppContext를 통해 DI(Container) 방식으로 연결됩니다.
