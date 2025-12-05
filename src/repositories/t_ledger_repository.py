"""Repository for T_Ledger sheet (auto-generated)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Any

from src.sheets.google_client import GoogleSheetsClient
from src.repositories.base import BaseSheetRepository


@dataclass
class TLedgerRow:
    timestamp: str | None = None
    symbol: str | None = None
    market: str | None = None
    side: str | None = None
    qty: str | None = None
    price: str | None = None
    amount_local: str | None = None
    currency: str | None = None
    fx_rate: str | None = None
    amount_krw: str | None = None
    fee_tax: str | None = None
    net_amount_krw: str | None = None
    order_id: str | None = None
    strategy: str | None = None
    position_after: str | None = None
    hold_days: str | None = None
    pnl: str | None = None
    pnl_pct: str | None = None
    tag: str | None = None
    broker: str | None = None
    note: str | None = None

class TLedgerRepository(BaseSheetRepository[TLedgerRow]):
    """
    T_Ledger 시트용 Repository (자동 생성 코드).
    - header_row: 1
    - data_start_row: 2
    - columns: Timestamp, Symbol, Market, Side, Qty, Price, Amount_Local, Currency, FX_Rate, Amount_KRW, Fee_Tax, Net_Amount_KRW, Order_ID, Strategy, Position_After, Hold_Days, PnL, PnL_Pct, Tag, Broker, Note
    """

    def __init__(self, client: GoogleSheetsClient) -> None:
        super().__init__(
            client=client,
            sheet_name="T_Ledger",
            header_row=1,
            data_start_row=2,
            columns=['Timestamp', 'Symbol', 'Market', 'Side', 'Qty', 'Price', 'Amount_Local', 'Currency', 'FX_Rate', 'Amount_KRW', 'Fee_Tax', 'Net_Amount_KRW', 'Order_ID', 'Strategy', 'Position_After', 'Hold_Days', 'PnL', 'PnL_Pct', 'Tag', 'Broker', 'Note'],
        )

    def parse_row(self, row: List[Any]) -> TLedgerRow:
        return TLedgerRow(
        timestamp=row[0] if len(row) > 0 else None,
        symbol=row[1] if len(row) > 1 else None,
        market=row[2] if len(row) > 2 else None,
        side=row[3] if len(row) > 3 else None,
        qty=row[4] if len(row) > 4 else None,
        price=row[5] if len(row) > 5 else None,
        amount_local=row[6] if len(row) > 6 else None,
        currency=row[7] if len(row) > 7 else None,
        fx_rate=row[8] if len(row) > 8 else None,
        amount_krw=row[9] if len(row) > 9 else None,
        fee_tax=row[10] if len(row) > 10 else None,
        net_amount_krw=row[11] if len(row) > 11 else None,
        order_id=row[12] if len(row) > 12 else None,
        strategy=row[13] if len(row) > 13 else None,
        position_after=row[14] if len(row) > 14 else None,
        hold_days=row[15] if len(row) > 15 else None,
        pnl=row[16] if len(row) > 16 else None,
        pnl_pct=row[17] if len(row) > 17 else None,
        tag=row[18] if len(row) > 18 else None,
        broker=row[19] if len(row) > 19 else None,
        note=row[20] if len(row) > 20 else None,
        )
