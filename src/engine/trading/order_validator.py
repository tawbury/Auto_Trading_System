# src/engine/trading/order_validator.py

from __future__ import annotations
from typing import Any

from .models import TradeSignal, OrderRequest

# 향후 RiskEngine 연결 예정
class OrderValidator:
    """
    OrderValidator:
    - 시그널(TradeSignal) 자체가 유효한지 체크
    - 주문(OrderRequest)이 리스크/규칙을 위반하는지 체크
    """

    def __init__(self, risk_engine: Any = None, pos_repo: Any = None, config: dict | None = None):
        self.risk_engine = risk_engine
        self.pos_repo = pos_repo
        self.config = config or {}

    # ------------------------------------------------------------
    # 1) 시그널 단위 검증
    # ------------------------------------------------------------
    def validate_signal(self, signal: TradeSignal) -> bool:
        """
        TradeSignal 자체의 유효성을 체크.
        예: KillSwitch, 전략 허용 여부, 시장 상태 체크 등
        """
        # KillSwitch
        if self.risk_engine and self.risk_engine.is_killswitch_on():
            print("[OrderValidator] KillSwitch ON → 시그널 차단")
            return False

        # 전략별 차단 규칙 (추후 확장)
        # if signal.strategy in self.config.get("blocked_strategies", []):
        #     return False

        return True

    # ------------------------------------------------------------
    # 2) 주문 레벨 검증
    # ------------------------------------------------------------
    def validate_order(self, order: OrderRequest) -> bool:
        """
        OrderRequest에 대해 RiskEngine 기반으로 주문 가능 여부 판단.
        - Exposure Limit
        - Max Position %
        - Max Position Count
        - Sector Limit
        등 추후 상세 구현.
        """
        if self.risk_engine:
            if not self.risk_engine.check_order_allowed(order):
                print("[OrderValidator] 리스크 한도 초과로 주문 차단")
                return False

        # 최소 거래 수량, 금액 제한 (옵션)
        # TODO: 설정값 기반 검증 추가

        return True
