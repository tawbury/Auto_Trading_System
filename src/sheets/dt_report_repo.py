# src/sheets/dt_report_repo.py
from typing import Dict, Any, List
from sheets.schema_loader import SchemaRegistry, SheetSchema
from sheets.google_client import GoogleSheetsClient


class DTReportRepository:
    def __init__(self, schema_registry: SchemaRegistry, gs: GoogleSheetsClient):
        self.schema: SheetSchema = schema_registry.get("DT_Report")
        self.gs = gs

    # ----------------------------------------------
    # row → dict 변환
    # ----------------------------------------------
    def row_to_dict(self, row: List[str]) -> Dict[str, Any]:
        result = {}
        for col_def, cell in zip(self.schema.columns, row):
            key = col_def.python_key
            result[key] = cell
        return result

    # ----------------------------------------------
    # 전체 시트 로드 (자동 매핑)
    # ----------------------------------------------
    def load_all(self) -> List[Dict[str, Any]]:
        rows = self.gs.read_all(self.schema.name)
        data_rows = rows[self.schema.row_start - 1:]   # row_start 기준
        result = []

        for r in data_rows:
            if len(r) == 0 or all(c == "" for c in r):
                continue
            result.append(self.row_to_dict(r))

        return result

    # ----------------------------------------------
    # 레코드 추가
    # ----------------------------------------------
    def append(self, record: Dict[str, Any]):
        row = []
        for col_def in self.schema.columns:
            key = col_def.python_key
            row.append(record.get(key, ""))

        ws = self.gs.get_sheet(self.schema.name)
        ws.append_row(row)
