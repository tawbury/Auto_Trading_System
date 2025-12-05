"""
SchemaDiffEngine — FINAL STABLE VERSION
---------------------------------------
Introspector가 리스트 또는 딕셔너리 형태로 컬럼을 생성해도
스키마 비교가 안정적으로 동작하도록 정규화 기능 포함.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any


class ChangeLevel(Enum):
    NONE = 0
    PATCH = 1
    MINOR = 2
    MAJOR = 3


class ChangeType(Enum):
    SHEET_ADDED = "sheet_added"
    SHEET_REMOVED = "sheet_removed"
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    COLUMN_TYPE_CHANGED = "column_type_changed"


@dataclass
class SchemaChange:
    path: str
    change_type: ChangeType
    level: ChangeLevel
    message: str


@dataclass
class SchemaDiffResult:
    changes: List[SchemaChange]

    @property
    def level(self) -> ChangeLevel:
        if not self.changes:
            return ChangeLevel.NONE
        return max((c.level for c in self.changes), key=lambda x: x.value)


class SchemaDiffEngine:

    # ---------------------------------------------------------
    # 컬럼 RAW 구조 정규화 (list → dict, dict → dict)
    # ---------------------------------------------------------
    def normalize_columns(self, cols_raw: Any) -> Dict[str, Dict[str, Any]]:
        """
        리스트 또는 딕셔너리든 모두 통일된 {col_name: {...}} 구조로 정규화.
        """

        normalized = {}

        if isinstance(cols_raw, dict):
            # 이미 dict 기반
            for key, val in cols_raw.items():
                normalized[key] = self.normalize_column(val)

        elif isinstance(cols_raw, list):
            # 리스트 기반 → 이름 키로 dict 변환
            for col_item in cols_raw:
                name = col_item.get("name") or col_item.get("column")
                if not name:
                    continue
                normalized[name] = self.normalize_column(col_item)

        else:
            # unexpected format
            return normalized

        return normalized

    # ---------------------------------------------------------
    # 컬럼 정의 유형 정규화
    # ---------------------------------------------------------
    @staticmethod
    def normalize_column(col_val: Any) -> Dict[str, Any]:
        """
        문자열이면 타입 unknown
        dict이면 column/type 보정
        """

        if isinstance(col_val, str):
            return {"column": col_val, "type": "unknown"}

        if isinstance(col_val, dict):
            return {
                "column": col_val.get("column", "unknown"),
                "type": col_val.get("type", col_val.get("datatype", "unknown"))
            }

        return {"column": "unknown", "type": "unknown"}

    # ---------------------------------------------------------
    # 메인 비교 함수
    # ---------------------------------------------------------
    def compare(self, old_schema: Dict[str, Any] | None, new_schema: Dict[str, Any]) -> SchemaDiffResult:
        changes: List[SchemaChange] = []

        # 스키마 신규 생성
        if old_schema is None:
            for sheet_name in new_schema.get("sheets", {}):
                changes.append(
                    SchemaChange(
                        path=f"sheets.{sheet_name}",
                        change_type=ChangeType.SHEET_ADDED,
                        level=ChangeLevel.MINOR,
                        message=f"Sheet '{sheet_name}' added (initial creation)"
                    )
                )
            return SchemaDiffResult(changes)

        old_sheets = old_schema.get("sheets", {})
        new_sheets = new_schema.get("sheets", {})

        # 시트 추가
        for sheet in new_sheets:
            if sheet not in old_sheets:
                changes.append(
                    SchemaChange(
                        path=f"sheets.{sheet}",
                        change_type=ChangeType.SHEET_ADDED,
                        level=ChangeLevel.MINOR,
                        message=f"Sheet '{sheet}' added"
                    )
                )

        # 시트 삭제
        for sheet in old_sheets:
            if sheet not in new_sheets:
                changes.append(
                    SchemaChange(
                        path=f"sheets.{sheet}",
                        change_type=ChangeType.SHEET_REMOVED,
                        level=ChangeLevel.MAJOR,
                        message=f"Sheet '{sheet}' removed"
                    )
                )

        # 컬럼 비교
        for sheet, new_meta in new_sheets.items():

            if sheet not in old_sheets:
                continue

            old_meta = old_sheets[sheet]

            new_cols = self.normalize_columns(new_meta.get("columns", {}))
            old_cols = self.normalize_columns(old_meta.get("columns", {}))

            new_keys = set(new_cols.keys())
            old_keys = set(old_cols.keys())

            # 컬럼 추가
            for col in new_keys - old_keys:
                changes.append(
                    SchemaChange(
                        path=f"sheets.{sheet}.columns.{col}",
                        change_type=ChangeType.COLUMN_ADDED,
                        level=ChangeLevel.PATCH,
                        message=f"Column '{col}' added"
                    )
                )

            # 컬럼 삭제
            for col in old_keys - new_keys:
                changes.append(
                    SchemaChange(
                        path=f"sheets.{sheet}.columns.{col}",
                        change_type=ChangeType.COLUMN_REMOVED,
                        level=ChangeLevel.MINOR,
                        message=f"Column '{col}' removed"
                    )
                )

            # 타입 변경
            for col in new_keys & old_keys:
                if new_cols[col] != old_cols[col]:
                    changes.append(
                        SchemaChange(
                            path=f"sheets.{sheet}.columns.{col}",
                            change_type=ChangeType.COLUMN_TYPE_CHANGED,
                            level=ChangeLevel.MINOR,
                            message=f"Column '{col}' changed: {old_cols[col]} → {new_cols[col]}"
                        )
                    )

        return SchemaDiffResult(changes)
