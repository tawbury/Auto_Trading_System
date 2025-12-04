# tests/test_trading_engine_virtual.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pathlib import Path

from core.app_context import AppContext
from engine.trading.models import TradeSignal, OrderSide, MarketType

from brokers.virtual_broker import VirtualBroker
from engine.trading.order_executor import OrderExecutor

from tests.mock_price_service import MockPriceService


def run_virtual_test():
    print("=== Virtual TradingEngine Test Start ===")

    # 1) AppContext 생성
    ctx = AppContext(Path("."))

    # 2) PriceService mock 적용
    mock_price_service = MockPriceService()
    ctx.price_service = mock_price_service

    # 3) Virtual Broker 적용
    ctx.broker = VirtualBroker(price_service=mock_price_service)

    # 4) OrderExecutor를 VirtualBroker 기반으로 교체
    ctx.order_executor = OrderExecutor(ctx.broker)
    ctx.trading_engine.executor = ctx.order_executor

    print("[TEST] Virtual broker + mock price service 적용 완료")

    # 5) 테스트 TradeSignal 생성
    signal = TradeSignal(
        symbol="005930",
        market=MarketType.KR,
        side=OrderSide.BUY,
        strategy="TEST_STRATEGY"
    )

    # 6) 시그널 등록 및 실행
    ctx.trading_engine.submit_signal(signal)
    ctx.trading_engine.process_all()

    print("[TEST] TradingEngine process_all() 실행 완료")

    # 7) DT_Report 기록 확인
    recent = ctx.dt_repo.load_recent(3)
    print("[TEST] 최근 DT_Report 기록:")
    for r in recent:
        print(r)

    print("=== Virtual TradingEngine Test Finished ===")


if __name__ == "__main__":
    run_virtual_test()
