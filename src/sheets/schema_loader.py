# src/sheets/schema_loader.py
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SheetColumn:
    col: str            # 예: "A"
    name: str           # 예: "Date"
    type: str           # 예: "string", "float"
    python_key: str     # 파이썬 dict에서 쓰는 이름 (예: date)


@dataclass
class SheetSchema:
    name: str
    sheet_type: str             # "DB" or "BLOCK"
    row_start: int
    columns: List[SheetColumn]
    primary_key: Optional[List[str]] = None
    relations: Optional[Dict] = None
    blocks: Optional[Dict] = None


class SchemaRegistry:
    def __init__(self, schema_path: Path):
        with schema_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        self.version = raw.get("version")
        self.project = raw.get("project")

        self._schemas: Dict[str, SheetSchema] = {}

        for sheet_name, sdef in raw["sheets"].items():
            columns = [
                SheetColumn(
                    col=c["col"],
                    name=c["name"],
                    type=c["type"],
                    python_key=c["python_key"]
                )
                for c in sdef.get("columns", [])
            ]

            schema = SheetSchema(
                name=sheet_name,
                sheet_type=sdef["type"],
                row_start=sdef["row_start"],
                columns=columns,
                primary_key=sdef.get("primary_key"),
                relations=sdef.get("relations"),
                blocks=sdef.get("blocks")
            )

            self._schemas[sheet_name] = schema

    def get(self, sheet_name: str) -> SheetSchema:
        return self._schemas[sheet_name]

    @property
    def sheets(self):
        return self._schemas
