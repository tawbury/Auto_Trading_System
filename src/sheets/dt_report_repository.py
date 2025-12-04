# src/sheets/dt_report_repository.py
from __future__ import annotations

from typing import Any, Dict, List

from .base_repository import BaseSheetRepository
from .schema_registry import SchemaRegistry
from .google_client import GoogleSheetsClient

# Trading Engine 쪽에서 정의할 예정
from src.engine.trading.models import OrderResult  # 예시 경로


class DTReportRepository(BaseSheetRepository):
    def __init__(self, schema_registry: SchemaRegistry, gs: GoogleSheetsClient):
        super().__init__(schema_registry, "DT_Report", gs)

    def load_recent(self, n: int = 100) -> List[Dict[str, Any]]:
        all_rows = self.load_all(max_rows=n)
        return all_rows

    def get_next_no(self) -> int:
        """
        A열(No) 기준으로 마지막 번호 + 1 반환.
        (단순 구현: 마지막 행 번호를 읽고 +1)
        """
        rows = self.load_all(max_rows=2000)
        if not rows:
            return 1
        # 마지막 유효 행의 no 컬럼 읽기
        last_no = 0
        for r in rows:
            try:
                no_val = int(r.get("no") or 0)
                if no_val > last_no:
                    last_no = no_val
            except ValueError:
                continue
        return last_no + 1

    def write_trade(self, result: OrderResult) -> None:
        """
        OrderResult를 DT_Report 시트 한 행으로 기록.
        계산 컬럼(PnL, PnL_Pct 등)은 시트 수식에 맡기고, 입력 필드만 채운다.
        auto_trading_system_v2.1.schema.json의 컬럼 키를 기준으로 매핑. :contentReference[oaicite:5]{index=5}
        """
        record: Dict[str, Any] = {
            "no": self.get_next_no(),
            "date": result.timestamp.strftime("%Y-%m-%d"),
            "time": result.timestamp.strftime("%H:%M:%S"),
            "symbol": result.symbol,
            "name": "",  # 종목명은 별도 데이터 소스 또는 시트 수식으로 채울 수 있음
            "market": result.market,
            "side": result.side,
            "qty": result.qty,
            "price": result.avg_price,
            "amount_local": result.amount_local,
            "currency": result.currency,
            "fx_rate": result.fx_rate,
            "amount_krw": result.amount_krw,
            "fee_tax": result.fee_tax,
            "net_amount_krw": result.amount_krw - result.fee_tax,
            "strategy": result.raw.get("strategy", "") if result.raw else "",
            "position_size": "",  # 체결 후 보유 수량은 Position에서 관리 가능
            "hold_days": "",
            "pnl": "",
            "pnl_pct": "",
            "tag": "",
            "note": "",
        }
        self.append(record)
