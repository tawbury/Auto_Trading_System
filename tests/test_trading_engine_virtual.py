# tests/test_trading_engine_virtual.py

from pathlib import Path

from core.app_context import AppContext

# TradingEngine Models
from engine.trading.models import TradeSignal, OrderSide, MarketType

# Virtual Broker
from brokers.virtual_broker import VirtualBroker

# TradingEngine 관련
from engine.trading.order_executor import OrderExecutor


def test_virtual_trading():
    """
    TradingEngine 전체 플로우 테스트 (가상 체결 환경)
    실거래 API 호출 없이 TradingEngine → Repo → Sheets까지 전체 검증 가능
    """

    # 1) AppContext 불러오기
    ctx = AppContext(Path("."))

    # 2) VirtualBroker로 교체
    ctx.broker = VirtualBroker(price_service=ctx.price_service)

    # 3) OrderExecutor도 VirtualBroker 기반으로 교체
    ctx.order_executor = OrderExecutor(ctx.broker)

    # TradingEngine 객체도 교체된 executor로 재생성
    ctx.trading_engine.executor = ctx.order_executor

    print("[TEST] Virtual TradingEngine 환경 구성 완료")

    # 4) 테스트용 시그널 생성
    test_signal = TradeSignal(
        symbol="005930",
        market=MarketType.KR,
        side=OrderSide.BUY,
        strategy="TEST_SIGNAL"
    )

    # 5) 시그널 등록
    ctx.trading_engine.submit_signal(test_signal)

    # 6) 처리 실행
    ctx.trading_engine.process_all()

    print("[TEST] TradingEngine process_all() 완료")

    # 7) 결과 확인 (DT_Report 마지막 행 검사)
    recent_rows = ctx.dt_repo.load_recent(5)
    print("[TEST] 최근 기록된 DT_Report 데이터:")
    for row in recent_rows:
        print(row)

    print("[TEST] Virtual Trading Test Finished Successfully.")
