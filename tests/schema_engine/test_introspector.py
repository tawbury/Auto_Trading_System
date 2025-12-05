# tests/schema_engine/test_introspector.py

import pytest
from tools.schema.sheets_introspector import SheetsIntrospector, SheetConfig, RawSchemaMeta

class DummySheetsClient:
    """가짜 Google Sheets Client"""
    def read_range(self, sheet_name, range_a1):
        if sheet_name == "Position":
            # Header row (42)
            if range_a1 == "A42:AD42":
                return [["Ticker", "Qty", "AvgPrice", "NowPrice", "Sector"]]
            # Sample rows
            return [
                ["005930", 10, 72000, 73000, "Tech"],
                ["000660", 5, 113000, 120000, "Semi"],
            ]
        raise ValueError("Unknown sheet")

def test_introspector_basic():
    client = DummySheetsClient()
    introspector = SheetsIntrospector(client)

    config = SheetConfig(
        name="Position",
        header_row=42,
        data_start_row_hint=43,
        max_columns=30,
        sample_row_count=10,
    )

    raw_schema = introspector.introspect([config])
    assert isinstance(raw_schema, RawSchemaMeta)
    assert "Position" in raw_schema.sheets

    sheet = raw_schema.sheets["Position"]
    assert sheet.row_start == 43
    assert len(sheet.columns) == 5

    # python_key 생성 검증
    keys = [c.python_key for c in sheet.columns]
    assert keys == ["ticker", "qty", "avgprice", "nowprice", "sector"]
