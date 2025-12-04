# src/engine/trading/position_sizer.py

from __future__ import annotations
from typing import Any

from .models import TradeSignal, OrderRequest, MarketType, OrderSide, OrderType


class PositionSizer:
    """
    PositionSizer:
    - 전략별 포지션 비중 결정
    - 자본(equity) 기반 계산
    - 시장(국내/해외)에 따라 브로커/환율 옵션 값 조정 가능
    """

    def __init__(self, price_service: Any, history_repo: Any, config: dict | None = None):
        self.price_service = price_service
        self.history_repo = history_repo
        self.config = config or {}

    # ------------------------------------------------------------
    # 전략별 기본 리스크 비율 가져오기
    # ------------------------------------------------------------
    def _get_risk_pct(self, strategy: str) -> float:
        # 추후 Config 시트 기반으로 가져올 수 있음
        return float(self.config.get("default_risk_pct", 0.1))

    # ------------------------------------------------------------
    # 메인 로직: 시그널 → 주문 요청
    # ------------------------------------------------------------
    def from_signal(self, signal: TradeSignal) -> OrderRequest:
        # 현재가 조회
        price = self.price_service.get_live_price(signal.symbol, signal.market)

        # 현재 Equity 가져오기
        equity = self.history_repo.get_latest_equity() or 0

        # 리스크 비율
        risk_pct = self._get_risk_pct(signal.strategy)

        # 포지션 노출 금액
        notional = equity * risk_pct

        # 수량 계산
        qty = 0
        if price > 0:
            qty = notional / price

        return OrderRequest(
            symbol=signal.symbol,
            market=signal.market,
            side=signal.side,
            qty=qty,
            order_type=OrderType.MARKET,
            strategy=signal.strategy,
            broker="",    # OrderExecutor가 결정할 수도 있음
        )
