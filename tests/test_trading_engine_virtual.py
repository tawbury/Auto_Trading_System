# tests/test_trading_engine_virtual.py

import sys
import os

# --------------------------------------------------------
# 1) 정확한 PYTHONPATH 설정 (테스트 환경 안정화)
# --------------------------------------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TESTS_DIR = os.path.abspath(os.path.dirname(__file__))

# 프로젝트 루트 및 src, tests 폴더 모두 추가
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))
sys.path.insert(0, TESTS_DIR)

# --------------------------------------------------------
# 2) 정상 import 가능한지 확인
# --------------------------------------------------------
from pathlib import Path

from core.app_context import AppContext
from engine.trading.models import TradeSignal, OrderSide, MarketType
from brokers.virtual_broker import VirtualBroker
from engine.trading.order_executor import OrderExecutor

# 여기서 import 실패하면 tests/mock_price_service.py 위치 오류!
from tests.mock_price_service import MockPriceService


# --------------------------------------------------------
# 3) 테스트 루틴
# --------------------------------------------------------
def run_virtual_test():
    print("=== Virtual TradingEngine Test Start ===")

    # 1) AppContext 생성
    ctx = AppContext(Path("."))

    # 2) PriceService mock 적용
    mock_price_service = MockPriceService()
    ctx.price_service = mock_price_service

    # 3) Virtual Broker 사용
    ctx.broker = VirtualBroker(price_service=mock_price_service)

    # 4) OrderExecutor 교체
    ctx.order_executor = OrderExecutor(ctx.broker)
    ctx.trading_engine.executor = ctx.order_executor

    print("[TEST] Virtual broker + mock price service 적용 완료")

    # 5) 시그널 생성
    signal = TradeSignal(
        symbol="005930",
        market=MarketType.KR,
        side=OrderSide.BUY,
        strategy="TEST_STRATEGY"
    )

    # 6) 실행
    ctx.trading_engine.submit_signal(signal)
    ctx.trading_engine.process_all()

    print("[TEST] TradingEngine process_all() 실행 완료")

    # 7) DT_Report 기록 조회
    recent = ctx.dt_repo.load_recent(3)
    print("[TEST] 최근 DT_Report 기록:")
    for r in recent:
        print(r)

    print("=== Virtual TradingEngine Test Finished ===")


# --------------------------------------------------------
# 4) 메인 실행
# --------------------------------------------------------
if __name__ == "__main__":
    run_virtual_test()
