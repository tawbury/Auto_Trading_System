# src/sheets/position_repository.py
from __future__ import annotations

from typing import Any, Dict, List

from .base_repository import BaseSheetRepository
from .schema_registry import SchemaRegistry
from .google_client import GoogleSheetsClient
from src.engine.trading.models import OrderResult  # 예시 경로


class PositionRepository(BaseSheetRepository):
    def __init__(self, schema_registry: SchemaRegistry, gs: GoogleSheetsClient):
        super().__init__(schema_registry, "Position", gs)

    def load_positions(self) -> List[Dict[str, Any]]:
        return self.load_all(max_rows=500)

    def find_position(self, symbol: str, market: str | None = None) -> Dict[str, Any] | None:
        for pos in self.load_positions():
            if pos.get("symbol") == symbol and (market is None or pos.get("market") == market):
                return pos
        return None

    def update_with_result(self, result: OrderResult) -> None:
        """
        OrderResult 기반으로 Position 시트를 업데이트.
        - BUY: 수량 증가 / 평균단가 재계산
        - SELL: 수량 감소 / 0이 되면 행 제거 또는 0 표시
        여기서는 스캐폴드 수준으로 'TODO' 형태로 남겨두고,
        실제 시트 업데이트는 후속 단계에서 구체화한다.
        """
        # 1) 전체 포지션 읽기
        positions = self.load_positions()

        # 2) 심볼 매칭
        #   - 실제 구현에서는 시트 행 번호까지 함께 관리하는 편이 좋다.
        #   - 지금은 스캐폴드이므로 pseudo 코드 수준으로 둔다.
        # TODO: 시트 행 인덱스를 함께 관리하여 update_range 호출

        # 예시 placeholder:
        # if result.side == "BUY":
        #     ...
        # elif result.side == "SELL":
        #     ...

        # 현재 단계에서는 단순히 "읽기 기반 설계"까지만 두고,
        # 실제 update 로직은 Position 수식/구조가 확정된 다음 채운다.
        pass
