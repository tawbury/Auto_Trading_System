# src/sheets/history_repository.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import date, datetime

from .base_repository import BaseSheetRepository
from .schema_registry import SchemaRegistry
from .google_client import GoogleSheetsClient


class HistoryRepository(BaseSheetRepository):
    def __init__(self, schema_registry: SchemaRegistry, gs: GoogleSheetsClient):
        super().__init__(schema_registry, "History", gs)

    def load_history(self, max_rows: int = 2000) -> List[Dict[str, Any]]:
        return self.load_all(max_rows=max_rows)

    def get_latest_equity(self) -> Optional[float]:
        rows = self.load_history(max_rows=365)
        latest_equity = None
        latest_date = None

        for r in rows:
            d = r.get("date")
            eq = r.get("total_equity")
            if not d or not eq:
                continue
            try:
                # d가 문자열일 수 있으므로 파싱
                if isinstance(d, str):
                    d_parsed = date.fromisoformat(d)
                else:
                    d_parsed = d
                eq_val = float(eq)
            except Exception:
                continue

            if latest_date is None or d_parsed > latest_date:
                latest_date = d_parsed
                latest_equity = eq_val

        return latest_equity

    def append_daily_record(
        self,
        total_equity: float,
        daily_pnl: float,
        daily_return: float,
        note: str = "",
        record_date: date | None = None,
    ) -> None:
        if record_date is None:
            record_date = date.today()

        record: Dict[str, Any] = {
            "date": record_date.isoformat(),
            "total_equity": total_equity,
            "daily_pnl": daily_pnl,
            "daily_return": daily_return,
            "cumulative_return": "",  # 시트 수식으로 처리
            "vol_20d": "",
            "high_watermark": "",
            "drawdown": "",
            "mdd": "",
            "note": note,
        }
        self.append(record)
