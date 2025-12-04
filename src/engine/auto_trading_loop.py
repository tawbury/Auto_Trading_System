# src/engine/auto_trading_loop.py

import time
from datetime import datetime


class AutoTradingLoop:
    """
    자동매매 메인 루프.

    전체 흐름:
    --------------------------------------
    1) KillSwitch 상태 확인
    2) 포트폴리오 평가 (PortfolioEngine)
    3) 리스크 엔진 검사 (RiskEngine)
    4) 전략 시그널 생성 (StrategyEngine)
    5) 매수/매도 실행 (Broker)
    6) 실행 결과 Google Sheet 기록
    --------------------------------------

    특징:
    - 국내(KR) + 해외(US/HK) 통합 구조 유지
    - 해외 주문 코드는 현재 모의투자에서 불가 → 주석 처리해 유지
    - 실전전환(REAL) 또는 외부 API 적용 시 즉시 활성화 가능
    """

    def __init__(
            self,
            broker,
            strategy_engine,
            portfolio_engine,
            risk_engine,
            sheet_client,
            interval_sec=60
    ):
        self.broker = broker
        self.strategy_engine = strategy_engine
        self.portfolio_engine = portfolio_engine
        self.risk_engine = risk_engine
        self.sheet = sheet_client
        self.interval = interval_sec

        # KillSwitch 상태 (Config 시트에서 읽어올 수도 있음)
        self.kill_switch = False

    # =====================================================================
    # 루프 시작
    # =====================================================================
    def start(self):
        print("\n=== Auto Trading Loop Start ===\n")

        while True:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{now}] ===== 자동매매 루프 실행 =====")

            # -------------------------------------------------------------
            # 0) KillSwitch 검사
            # -------------------------------------------------------------
            if self.kill_switch:
                print("[KILL SWITCH] 자동매매 정지됨 (매매 스킵)")
                time.sleep(self.interval)
                continue

            # -------------------------------------------------------------
            # 1) 포트폴리오 평가
            # -------------------------------------------------------------
            portfolio_state = self.portfolio_engine.build_portfolio_state()
            print("[INFO] 포트폴리오 평가 완료")

            # -------------------------------------------------------------
            # 2) 리스크 체크
            # -------------------------------------------------------------
            risk_ok = self.risk_engine.check_all(portfolio_state)
            if not risk_ok:
                print("[RISK] 리스크 제한 초과 → 매매 스킵")
                time.sleep(self.interval)
                continue

            # -------------------------------------------------------------
            # 3) 전략 엔진 실행
            # -------------------------------------------------------------
            signals = self.strategy_engine.generate_signals(portfolio_state)

            if not signals:
                print("[STRATEGY] 시그널 없음 → 대기")
                time.sleep(self.interval)
                continue

            print(f"[STRATEGY] 시그널 {len(signals)}개 감지")

            # -------------------------------------------------------------
            # 4) 시그널 처리 (국내/해외 매매 포함)
            # -------------------------------------------------------------
            for sig in signals:
                action = sig.get("type")
                symbol = sig.get("symbol")
                qty = sig.get("qty", 0)
                price = sig.get("price", 0)
                market = sig.get("market", "KR").upper()

                print(f"[SIGNAL] {market} / {action} / {symbol} / {qty}")

                # ---------------------------
                # 국내 주식 주문 처리
                # ---------------------------
                if market == "KR":

                    if action == "BUY":
                        print(f"[ORDER] 국내 매수 요청: {symbol}, {qty}")
                        result = self.broker.buy(
                            symbol=symbol,
                            qty=qty,
                            order_type="03"  # 시장가
                        )

                    elif action == "SELL":
                        print(f"[ORDER] 국내 매도 요청: {symbol}, {qty}")
                        result = self.broker.sell(
                            symbol=symbol,
                            qty=qty,
                            order_type="03"
                        )

                    else:
                        print(f"[SKIP] 알 수 없는 타입: {action}")
                        continue

                # ---------------------------
                # 해외 주식 주문 처리 (주석)
                # ---------------------------
                else:
                    print(f"[OVERSEAS] 해외 종목 주문 감지됨: {market} {symbol}")

                    # ※ KIS 모의투자에서는 해외 주문이 동작하지 않으므로
                    # 아래 코드는 향후 실전 모드에서 활성화
                    #
                    # if action == "BUY":
                    #     result = self.broker.buy_overseas(
                    #         symbol=symbol,
                    #         exch=market,
                    #         qty=qty
                    #     )
                    # elif action == "SELL":
                    #     result = self.broker.sell_overseas(
                    #         symbol=symbol,
                    #         exch=market,
                    #         qty=qty
                    #     )
                    # else:
                    #     print("[OVERSEAS] 알 수 없는 시그널 타입")
                    #     continue
                    #
                    # 해외는 현재 무조건 스킵
                    result = None

                # ---------------------------------------------------------
                # 5) 주문 성공 시 Google Sheets 기록
                # ---------------------------------------------------------
                if result:
                    print("[SHEET] 거래 기록 저장")
                    try:
                        self.sheet.append_trade(result, sig)
                    except Exception as e:
                        print("[SHEET ERROR] 기록 실패:", str(e))

            # -------------------------------------------------------------
            # 6) 대기 후 다음 루프 실행
            # -------------------------------------------------------------
            print(f"[LOOP] {self.interval}초 대기 후 다음 루프 실행\n")
            time.sleep(self.interval)
