# src/sheets/position_repo.py
from typing import Dict, Any, List
from sheets.schema_loader import SchemaRegistry, SheetSchema
from sheets.google_client import GoogleSheetsClient


class PositionRepository:
    def __init__(self, schema_registry: SchemaRegistry, gs: GoogleSheetsClient):
        self.schema: SheetSchema = schema_registry.get("Position")
        self.gs = gs

    # -------------------------------------------------------
    # 시트 row → dict 변환
    # -------------------------------------------------------
    def row_to_dict(self, row: List[str]) -> Dict[str, Any]:
        result = {}
        for col_def, cell in zip(self.schema.columns, row):
            key = col_def.python_key
            result[key] = cell
        return result

    # -------------------------------------------------------
    # 전체 Position 로드
    # -------------------------------------------------------
    def load_all(self) -> List[Dict[str, Any]]:
        rows = self.gs.read_all(self.schema.name)
        data_rows = rows[self.schema.row_start - 1:]  # row_start 기준

        result = []
        for r in data_rows:
            if len(r) == 0 or all(c == "" for c in r):
                continue
            result.append(self.row_to_dict(r))
        return result
