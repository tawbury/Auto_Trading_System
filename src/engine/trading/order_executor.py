# src/engine/trading/order_executor.py

from __future__ import annotations
from typing import Any

from .models import OrderRequest, OrderResult


class OrderExecutor:
    """
    OrderExecutor:
    - BrokerInterface 기반으로 실 거래 요청 수행
    - OrderResult를 표준화하여 반환
    """

    def __init__(self, broker: Any):
        self.broker = broker

    # ------------------------------------------------------------
    # 주문 실행
    # ------------------------------------------------------------
    def execute(self, order: OrderRequest) -> OrderResult:
        """
        BrokerInterface:
            buy(order: OrderRequest) -> OrderResult
            sell(order: OrderRequest) -> OrderResult
        """

        if order.side == order.side.BUY:
            result = self.broker.buy(order)
        else:
            result = self.broker.sell(order)

        # result는 KISBroker에서 반환하는 dict 또는 class일 수 있음
        # TradingEngine이 표준 OrderResult로 사용해야 하므로 확인/변환 필요

        if isinstance(result, OrderResult):
            return result

        # 브로커 응답이 dict라면 OrderResult 변환
        return OrderResult(
            order_id=result.get("order_id", ""),
            symbol=order.symbol,
            market=order.market,
            side=order.side,
            qty=order.qty,
            avg_price=result.get("avg_price", 0),
            fee_tax=result.get("fee_tax", 0),
            amount_local=result.get("amount_local", 0),
            currency=result.get("currency", "KRW"),
            fx_rate=result.get("fx_rate", 1),
            amount_krw=result.get("amount_krw", 0),
            broker=result.get("broker", "KIS"),
            raw=result,
        )
