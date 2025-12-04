# src/sheets/base_repository.py
from __future__ import annotations

from typing import Any, Dict, List

from .schema_registry import SchemaRegistry, SheetSchema
from .google_client import GoogleSheetsClient


class BaseSheetRepository:
    def __init__(
        self,
        schema_registry: SchemaRegistry,
        sheet_name: str,
        gs: GoogleSheetsClient,
    ):
        self.sheet_name = sheet_name
        self.schema: SheetSchema = schema_registry.get(sheet_name)
        self.gs = gs

        # python_key -> column letter
        self.col_by_key = {
            col_def["python_key"]: col_def["col"]
            for col_def in self.schema.columns
            if "python_key" in col_def
        }

        # 유지: row_start (기본 2행)
        self.row_start = self.schema.row_start

    # ---- 공통 유틸 ----
    def _build_a1_range(self, start_row: int, end_row: int) -> str:
        if not self.schema.columns:
            raise ValueError(f"No columns defined for sheet: {self.sheet_name}")
        first_col = self.schema.columns[0]["col"]
        last_col = self.schema.columns[-1]["col"]
        return f"{first_col}{start_row}:{last_col}{end_row}"

    def _row_to_dict(self, row: List[Any]) -> Dict[str, Any]:
        """
        시트 한 줄(row)을 python_key 기반 dict로 변환.
        """
        record: Dict[str, Any] = {}
        for idx, col_def in enumerate(self.schema.columns):
            key = col_def.get("python_key")
            if not key:
                continue
            if idx < len(row):
                record[key] = row[idx]
            else:
                record[key] = None
        return record

    def _dict_to_row(self, record: Dict[str, Any]) -> List[Any]:
        """
        python_key dict를 시트의 컬럼 순서 행(list)로 변환.
        계산용/수식용 컬럼은 비워두면 된다.
        """
        row: List[Any] = []
        for col_def in self.schema.columns:
            key = col_def.get("python_key")
            if not key:
                row.append("")  # 또는 None
            else:
                row.append(record.get(key, ""))
        return row

    # ---- 공통 메서드 ----
    def load_all(self, max_rows: int = 2000) -> List[Dict[str, Any]]:
        """
        row_start부터 max_rows까지 읽어 dict 리스트로 반환.
        빈 행만 나온 이후는 무시하는 형태로 최적화 가능.
        """
        start = self.row_start
        end = self.row_start + max_rows - 1
        a1 = self._build_a1_range(start, end)
        values = self.gs.read_range(self.sheet_name, a1) or []
        records: List[Dict[str, Any]] = []

        for idx, row in enumerate(values):
            # 완전히 빈 행이면 이후는 스킵해도 됨
            if not any(str(cell).strip() for cell in row):
                # 여기서 break를 걸면 더 빠르지만 상황에 따라 조정
                continue
            records.append(self._row_to_dict(row))
        return records

    def append(self, record: Dict[str, Any]) -> None:
        row = self._dict_to_row(record)
        self.gs.append_row(self.sheet_name, row)
