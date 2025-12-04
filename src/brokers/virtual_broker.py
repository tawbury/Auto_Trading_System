# src/brokers/virtual_broker.py

from __future__ import annotations
from datetime import datetime

from engine.trading.models import OrderRequest, OrderResult


class VirtualBroker:
    """
    테스트용 가상 브로커 (실거래 요청 없음)
    - 실제 API 호출 대신 즉시 체결 처리
    """

    def __init__(self, price_service):
        self.price_service = price_service

    # ------------------------------------------------------------
    # 공통 체결 생성 로직
    # ------------------------------------------------------------
    def _make_result(self, order: OrderRequest) -> OrderResult:
        # 현재 가격 조회
        price = self.price_service.get_live_price(order.symbol, order.market)

        amount_local = price * order.qty
        amount_krw = amount_local * 1  # currency가 KRW가 아닌 경우 수정 가능

        return OrderResult(
            order_id=f"VIRTUAL-{datetime.utcnow().timestamp()}",
            symbol=order.symbol,
            market=order.market,
            side=order.side,
            qty=order.qty,
            avg_price=price,
            fee_tax=0,
            amount_local=amount_local,
            currency="KRW",
            fx_rate=1,
            amount_krw=amount_krw,
            broker="VIRTUAL",
            raw={"source": "virtual_broker"},
        )

    # ------------------------------------------------------------
    # BUY
    # ------------------------------------------------------------
    def buy(self, order: OrderRequest) -> OrderResult:
        return self._make_result(order)

    # ------------------------------------------------------------
    # SELL
    # ------------------------------------------------------------
    def sell(self, order: OrderRequest) -> OrderResult:
        return self._make_result(order)
