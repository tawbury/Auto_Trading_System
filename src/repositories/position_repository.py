"""Repository for Position sheet (auto-generated)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Any

from src.sheets.google_client import GoogleSheetsClient
from src.repositories.base import BaseSheetRepository


@dataclass
class PositionRow:
    symbol: str | None = None
    name: str | None = None
    market: str | None = None
    qty: str | None = None
    avg_price_current_currency: str | None = None
    current_price_current_currency: str | None = None
    avg_price_krw: str | None = None
    current_price_krw: str | None = None
    market_value_krw: str | None = None
    unrealized_pnl_krw: str | None = None
    unrealized_pnl_pct: str | None = None
    strategy: str | None = None
    atr: str | None = None
    atr_pct: str | None = None
    last_atr_pct: str | None = None
    atr_stop: str | None = None
    atr_target: str | None = None
    sector: str | None = None
    tag: str | None = None
    note: str | None = None

class PositionRepository(BaseSheetRepository[PositionRow]):
    """
    Position 시트용 Repository (자동 생성 코드).
    - header_row: 1
    - data_start_row: 2
    - columns: Symbol, Name, Market, Qty, Avg_Price(Current_Currency), Current_Price(Current_Currency), Avg_Price_KRW, Current_Price_KRW, Market_Value_KRW, Unrealized_PnL_KRW, Unrealized_PnL_Pct, Strategy, ATR, ATR_Pct, Last_ATR_Pct, ATR_Stop, ATR_Target, Sector, Tag, Note
    """

    def __init__(self, client: GoogleSheetsClient) -> None:
        super().__init__(
            client=client,
            sheet_name="Position",
            header_row=1,
            data_start_row=2,
            columns=['Symbol', 'Name', 'Market', 'Qty', 'Avg_Price(Current_Currency)', 'Current_Price(Current_Currency)', 'Avg_Price_KRW', 'Current_Price_KRW', 'Market_Value_KRW', 'Unrealized_PnL_KRW', 'Unrealized_PnL_Pct', 'Strategy', 'ATR', 'ATR_Pct', 'Last_ATR_Pct', 'ATR_Stop', 'ATR_Target', 'Sector', 'Tag', 'Note'],
        )

    def parse_row(self, row: List[Any]) -> PositionRow:
        return PositionRow(
        symbol=row[0] if len(row) > 0 else None,
        name=row[1] if len(row) > 1 else None,
        market=row[2] if len(row) > 2 else None,
        qty=row[3] if len(row) > 3 else None,
        avg_price_current_currency=row[4] if len(row) > 4 else None,
        current_price_current_currency=row[5] if len(row) > 5 else None,
        avg_price_krw=row[6] if len(row) > 6 else None,
        current_price_krw=row[7] if len(row) > 7 else None,
        market_value_krw=row[8] if len(row) > 8 else None,
        unrealized_pnl_krw=row[9] if len(row) > 9 else None,
        unrealized_pnl_pct=row[10] if len(row) > 10 else None,
        strategy=row[11] if len(row) > 11 else None,
        atr=row[12] if len(row) > 12 else None,
        atr_pct=row[13] if len(row) > 13 else None,
        last_atr_pct=row[14] if len(row) > 14 else None,
        atr_stop=row[15] if len(row) > 15 else None,
        atr_target=row[16] if len(row) > 16 else None,
        sector=row[17] if len(row) > 17 else None,
        tag=row[18] if len(row) > 18 else None,
        note=row[19] if len(row) > 19 else None,
        )
