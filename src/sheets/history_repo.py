# src/sheets/history_repo.py
from typing import Dict, Any, List
from sheets.schema_loader import SchemaRegistry, SheetSchema
from sheets.google_client import GoogleSheetsClient


class HistoryRepository:
    def __init__(self, schema_registry: SchemaRegistry, gs: GoogleSheetsClient):
        self.schema: SheetSchema = schema_registry.get("History")
        self.gs = gs

    def row_to_dict(self, row: List[str]) -> Dict[str, Any]:
        result = {}
        for col_def, cell in zip(self.schema.columns, row):
            result[col_def.python_key] = cell
        return result

    def load_all(self) -> List[Dict[str, Any]]:
        rows = self.gs.read_all(self.schema.name)
        data_rows = rows[self.schema.row_start - 1:]

        result = []
        for r in data_rows:
            if len(r) == 0 or all(c == "" for c in r):
                continue
            result.append(self.row_to_dict(r))
        return result
