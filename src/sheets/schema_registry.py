# src/sheets/schema_registry.py
import json
from pathlib import Path
from typing import Any, Dict


class SheetSchema:
    def __init__(self, name: str, raw: Dict[str, Any]):
        self.name = name
        self.raw = raw
        self.row_start: int = raw.get("row_start", 2)
        self.columns = raw.get("columns", [])
        self.primary_key = raw.get("primary_key", [])
        self.blocks = raw.get("blocks", {})

        # python_key -> column letter (e.g. "symbol" -> "A")
        self._col_by_key = {
            col_def.get("python_key"): col_def.get("col")
            for col_def in self.columns
            if col_def.get("python_key")
        }

    def get_column_letter(self, python_key: str) -> str | None:
        return self._col_by_key.get(python_key)

    def get_blocks(self) -> Dict[str, Any]:
        return self.blocks


class SchemaRegistry:
    def __init__(self, schema_path: Path):
        self.schema_path = schema_path
        self._schemas: Dict[str, SheetSchema] = {}
        self._load()

    def _load(self) -> None:
        with self.schema_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        sheets_raw = data.get("sheets", {})
        for sheet_name, sheet_def in sheets_raw.items():
            # Config 같은 특수 sheet에 type/fields가 추가로 있을 수 있음
            if not isinstance(sheet_def, dict):
                continue
            self._schemas[sheet_name] = SheetSchema(sheet_name, sheet_def)

    def get(self, sheet_name: str) -> SheetSchema:
        if sheet_name not in self._schemas:
            raise KeyError(f"Sheet schema not found: {sheet_name}")
        return self._schemas[sheet_name]

    def all_sheet_names(self) -> list[str]:
        return list(self._schemas.keys())
