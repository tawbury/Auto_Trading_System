# src/engine/trading/trading_engine.py

from __future__ import annotations
from typing import Optional

from .models import TradeSignal, OrderRequest, OrderResult
from .event_queue import EventQueue
from .order_validator import OrderValidator
from .position_sizer import PositionSizer
from .order_executor import OrderExecutor

from sheets.dt_report_repository import DTReportRepository
from sheets.position_repository import PositionRepository
from sheets.history_repository import HistoryRepository


class TradingEngine:
    """
    TradingEngine:
    - TradeSignal 입력
    - OrderRequest 생성
    - Broker(OrderExecutor) 호출
    - OrderResult 기반 DT_Report, Position, History 업데이트
    """

    def __init__(
        self,
        dt_repo: DTReportRepository,
        pos_repo: PositionRepository,
        hist_repo: HistoryRepository,
        validator: OrderValidator,
        sizer: PositionSizer,
        executor: OrderExecutor,
    ):
        self.dt_repo = dt_repo
        self.pos_repo = pos_repo
        self.hist_repo = hist_repo

        self.validator = validator
        self.sizer = sizer
        self.executor = executor

        self.queue = EventQueue()

    # ============================================================
    # 1) 외부에서 시그널 등록
    # ============================================================
    def submit_signal(self, signal: TradeSignal) -> None:
        self.queue.push(signal)

    # ============================================================
    # 2) 시그널 하나 처리
    # ============================================================
    def process_once(self) -> None:
        signal = self.queue.pop()
        if signal is None:
            return
        self._handle_signal(signal)

    # ============================================================
    # 3) 큐가 빌 때까지 모두 처리
    # ============================================================
    def process_all(self) -> None:
        while not self.queue.empty():
            self.process_once()

    # ============================================================
    # 4) 내부 처리 로직
    # ============================================================
    def _handle_signal(self, signal: TradeSignal) -> None:

        # 1) 시그널 단위 검증 (RiskEngine 등 포함)
        if not self.validator.validate_signal(signal):
            return

        # 2) 포지션 사이즈 산출
        order_req: OrderRequest = self.sizer.from_signal(signal)

        # 3) 주문 레벨 검증
        if not self.validator.validate_order(order_req):
            return

        # 4) 브로커로 주문 실행
        order_result: OrderResult = self.executor.execute(order_req)

        # 5) DT_Report 기록
        self.dt_repo.write_trade(order_result)

        # 6) Position 업데이트 (TODO: 상세 구현)
        self.pos_repo.update_with_result(order_result)

        # 7) History 업데이트 (TODO: 상세 구현)
        self.hist_repo.update_after_trade(order_result)

        # (선택) 리스크엔진에 반영 (추후 연결)
        # self.risk_engine.update(order_result)
