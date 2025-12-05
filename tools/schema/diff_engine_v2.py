"""
diff_engine_v2.py

Schema Diff Engine v2
- Compares two ATS schema dictionaries and produces a structured diff result.
- Designed to work with the Master Schema used in the Auto Trading System project.

This module does NOT perform any file I/O. It only works with in-memory dicts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ChangeLevel(Enum):
    """Overall impact level of a schema change."""
    PATCH = auto()
    MINOR = auto()
    MAJOR = auto()
    BREAKING = auto()

    @classmethod
    def max_level(cls, levels: List["ChangeLevel"]) -> "ChangeLevel":
        if not levels:
            return ChangeLevel.PATCH
        # Order defines severity
        order = {
            ChangeLevel.PATCH: 0,
            ChangeLevel.MINOR: 1,
            ChangeLevel.MAJOR: 2,
            ChangeLevel.BREAKING: 3,
        }
        return max(levels, key=lambda lv: order[lv])


class ChangeType(Enum):
    """Type of schema change detected."""
    SCHEMA_METADATA_CHANGED = auto()
    SHEET_ADDED = auto()
    SHEET_REMOVED = auto()
    ROW_START_CHANGED = auto()
    COLUMN_ADDED = auto()
    COLUMN_REMOVED = auto()
    COLUMN_TYPE_CHANGED = auto()
    COLUMN_POSITION_CHANGED = auto()
    COLUMN_META_CHANGED = auto()
    BLOCKS_CHANGED = auto()
    UNKNOWN = auto()


@dataclass
class SchemaChange:
    """Represents a single change between old and new schema."""
    change_type: ChangeType
    level: ChangeLevel
    path: str  # e.g. "Position.columns[Qty]" or "Config.blocks"
    message: str
    old_value: Any = None
    new_value: Any = None


@dataclass
class SchemaDiffResult:
    """Aggregated diff result."""
    changes: List[SchemaChange]

    @property
    def level(self) -> ChangeLevel:
        """Overall impact level derived from all changes."""
        if not self.changes:
            return ChangeLevel.PATCH
        return ChangeLevel.max_level([c.level for c in self.changes])

    def is_empty(self) -> bool:
        return not self.changes


class SchemaDiffError(Exception):
    """Raised when diff cannot be computed."""
    pass


class SchemaDiffEngine:
    """
    SchemaDiffEngine compares two ATS schema dicts and produces a structured diff.

    Assumptions:
    - Schema is a dict loaded from schema JSON.
    - Sheets are either under top-level "sheets" key or as top-level sheet objects
      (excluding metadata keys like "version", "project").
    - Each sheet contains:
        - "row_start": optional int
        - "columns": list of column definitions with keys such as:
            - "name"
            - "python_key"
            - "col"
            - "type"
        - "blocks": optional dict
    """

    METADATA_KEYS = {"version", "project", "$schema", "meta"}

    def diff(self, old: Dict[str, Any], new: Dict[str, Any]) -> SchemaDiffResult:
        """
        Compute diff between old and new schema dictionaries.

        :param old: previous schema dict
        :param new: new schema dict
        :return: SchemaDiffResult
        """
        logger.debug("Starting schema diff computation")
        changes: List[SchemaChange] = []

        # 1) Top-level metadata (version, project, etc.)
        changes.extend(self._diff_metadata(old, new))

        # 2) Sheets
        old_sheets = self._extract_sheet_map(old)
        new_sheets = self._extract_sheet_map(new)

        changes.extend(self._diff_sheets(old_sheets, new_sheets))

        logger.info(
            "Schema diff completed: %d change(s), overall level=%s",
            len(changes),
            SchemaDiffResult(changes).level.name,
        )
        return SchemaDiffResult(changes)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _diff_metadata(self, old: Dict[str, Any], new: Dict[str, Any]) -> List[SchemaChange]:
        changes: List[SchemaChange] = []

        for key in self.METADATA_KEYS:
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                path = key
                msg = f"Metadata field '{key}' changed from {old_val!r} to {new_val!r}"
                # version/project 변경은 코드에 직접 영향은 적으므로 PATCH로 취급
                change = SchemaChange(
                    change_type=ChangeType.SCHEMA_METADATA_CHANGED,
                    level=ChangeLevel.PATCH,
                    path=path,
                    message=msg,
                    old_value=old_val,
                    new_value=new_val,
                )
                logger.debug("Detected metadata change: %s", msg)
                changes.append(change)
        return changes

    def _extract_sheet_map(self, schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extracts a map of sheet_name -> sheet_def from a schema dict.

        Priority:
        1) schema["sheets"] if exists and is dict
        2) otherwise, all top-level dict-valued keys except metadata keys
        """
        if "sheets" in schema and isinstance(schema["sheets"], dict):
            logger.debug("Schema uses 'sheets' key for sheet definitions")
            return schema["sheets"]

        sheets: Dict[str, Dict[str, Any]] = {}
        for key, value in schema.items():
            if key in self.METADATA_KEYS:
                continue
            if isinstance(value, dict):
                sheets[key] = value
        logger.debug("Extracted %d sheets from schema", len(sheets))
        return sheets

    def _diff_sheets(
        self,
        old_sheets: Dict[str, Dict[str, Any]],
        new_sheets: Dict[str, Dict[str, Any]],
    ) -> List[SchemaChange]:
        changes: List[SchemaChange] = []

        old_sheet_names = set(old_sheets.keys())
        new_sheet_names = set(new_sheets.keys())

        # Removed sheets
        for sheet_name in sorted(old_sheet_names - new_sheet_names):
            msg = f"Sheet '{sheet_name}' was removed"
            change = SchemaChange(
                change_type=ChangeType.SHEET_REMOVED,
                level=ChangeLevel.MAJOR,
                path=sheet_name,
                message=msg,
                old_value=old_sheets[sheet_name],
                new_value=None,
            )
            logger.debug("Detected sheet removal: %s", msg)
            changes.append(change)

        # Added sheets
        for sheet_name in sorted(new_sheet_names - old_sheet_names):
            msg = f"Sheet '{sheet_name}' was added"
            # 새 시트 추가는 기본적으로 MINOR로 보지만,
            # 시스템 의존도가 높다면 프로젝트 정책에 따라 MAJOR로 격상 가능.
            change = SchemaChange(
                change_type=ChangeType.SHEET_ADDED,
                level=ChangeLevel.MINOR,
                path=sheet_name,
                message=msg,
                old_value=None,
                new_value=new_sheets[sheet_name],
            )
            logger.debug("Detected sheet addition: %s", msg)
            changes.append(change)

        # Sheets present in both
        for sheet_name in sorted(old_sheet_names & new_sheet_names):
            old_sheet = old_sheets[sheet_name]
            new_sheet = new_sheets[sheet_name]
            sheet_path_prefix = sheet_name

            # row_start
            changes.extend(
                self._diff_row_start(
                    sheet_path_prefix,
                    old_sheet.get("row_start"),
                    new_sheet.get("row_start"),
                )
            )

            # columns
            changes.extend(
                self._diff_columns(
                    sheet_path_prefix,
                    old_sheet.get("columns", []),
                    new_sheet.get("columns", []),
                )
            )

            # blocks
            changes.extend(
                self._diff_blocks(
                    sheet_path_prefix,
                    old_sheet.get("blocks"),
                    new_sheet.get("blocks"),
                )
            )

        return changes

    def _diff_row_start(
        self,
        sheet_path_prefix: str,
        old_row_start: Optional[int],
        new_row_start: Optional[int],
    ) -> List[SchemaChange]:
        changes: List[SchemaChange] = []
        if old_row_start != new_row_start:
            path = f"{sheet_path_prefix}.row_start"
            msg = f"Row start changed in sheet '{sheet_path_prefix}' from {old_row_start} to {new_row_start}"
            # row_start 변경은 Sheet Reader의 인덱스가 틀어지므로 MAJOR
            change = SchemaChange(
                change_type=ChangeType.ROW_START_CHANGED,
                level=ChangeLevel.MAJOR,
                path=path,
                message=msg,
                old_value=old_row_start,
                new_value=new_row_start,
            )
            logger.debug("Detected row_start change: %s", msg)
            changes.append(change)
        return changes

    # -------------------------------------------------------------------------
    # Columns
    # -------------------------------------------------------------------------

    def _build_column_key(self, col_def: Dict[str, Any]) -> str:
        """
        Determine a stable identifier for a column.

        Priority:
        1) python_key
        2) name
        3) col (A, B, C ...)
        """
        if "python_key" in col_def and col_def["python_key"]:
            return str(col_def["python_key"])
        if "name" in col_def and col_def["name"]:
            return str(col_def["name"])
        if "col" in col_def and col_def["col"]:
            return str(col_def["col"])
        # Fallback to repr for safety
        return repr(col_def)

    def _index_columns(
        self,
        columns: List[Dict[str, Any]],
    ) -> Dict[str, Tuple[int, Dict[str, Any]]]:
        """
        Returns a dict of column_key -> (position_index, col_def)
        """
        indexed: Dict[str, Tuple[int, Dict[str, Any]]] = {}
        for idx, col_def in enumerate(columns):
            key = self._build_column_key(col_def)
            indexed[key] = (idx, col_def)
        return indexed

    def _diff_columns(
        self,
        sheet_path_prefix: str,
        old_columns: List[Dict[str, Any]],
        new_columns: List[Dict[str, Any]],
    ) -> List[SchemaChange]:
        changes: List[SchemaChange] = []

        old_indexed = self._index_columns(old_columns)
        new_indexed = self._index_columns(new_columns)

        old_keys = set(old_indexed.keys())
        new_keys = set(new_indexed.keys())

        # Column removed
        for col_key in sorted(old_keys - new_keys):
            _, old_col = old_indexed[col_key]
            path = f"{sheet_path_prefix}.columns[{col_key}]"
            msg = f"Column '{col_key}' removed from sheet '{sheet_path_prefix}'"
            change = SchemaChange(
                change_type=ChangeType.COLUMN_REMOVED,
                level=ChangeLevel.MAJOR,
                path=path,
                message=msg,
                old_value=old_col,
                new_value=None,
            )
            logger.debug("Detected column removal: %s", msg)
            changes.append(change)

        # Column added
        for col_key in sorted(new_keys - old_keys):
            _, new_col = new_indexed[col_key]
            path = f"{sheet_path_prefix}.columns[{col_key}]"
            msg = f"Column '{col_key}' added to sheet '{sheet_path_prefix}'"
            # 새 컬럼 추가는 기본적으로 MINOR (전략/엔진이 활용하지 않으면 영향 적음)
            change = SchemaChange(
                change_type=ChangeType.COLUMN_ADDED,
                level=ChangeLevel.MINOR,
                path=path,
                message=msg,
                old_value=None,
                new_value=new_col,
            )
            logger.debug("Detected column addition: %s", msg)
            changes.append(change)

        # Columns present in both
        for col_key in sorted(old_keys & new_keys):
            old_pos, old_col = old_indexed[col_key]
            new_pos, new_col = new_indexed[col_key]
            base_path = f"{sheet_path_prefix}.columns[{col_key}]"

            # Position change (index)
            if old_pos != new_pos:
                msg = (
                    f"Column '{col_key}' position changed in sheet '{sheet_path_prefix}' "
                    f"from index {old_pos} to {new_pos}"
                )
                change = SchemaChange(
                    change_type=ChangeType.COLUMN_POSITION_CHANGED,
                    level=ChangeLevel.MINOR,
                    path=base_path,
                    message=msg,
                    old_value=old_pos,
                    new_value=new_pos,
                )
                logger.debug("Detected column position change: %s", msg)
                changes.append(change)

            # Type change
            old_type = old_col.get("type")
            new_type = new_col.get("type")
            if old_type != new_type:
                msg = (
                    f"Column '{col_key}' type changed in sheet '{sheet_path_prefix}' "
                    f"from {old_type!r} to {new_type!r}"
                )
                change = SchemaChange(
                    change_type=ChangeType.COLUMN_TYPE_CHANGED,
                    level=ChangeLevel.MAJOR,
                    path=f"{base_path}.type",
                    message=msg,
                    old_value=old_type,
                    new_value=new_type,
                )
                logger.debug("Detected column type change: %s", msg)
                changes.append(change)

            # Meta changes (description, note, etc.) – treat as PATCH
            meta_keys = {"description", "note", "label"}
            for meta_key in meta_keys:
                old_meta = old_col.get(meta_key)
                new_meta = new_col.get(meta_key)
                if old_meta != new_meta:
                    msg = (
                        f"Column '{col_key}' meta field '{meta_key}' changed in sheet "
                        f"'{sheet_path_prefix}' from {old_meta!r} to {new_meta!r}"
                    )
                    change = SchemaChange(
                        change_type=ChangeType.COLUMN_META_CHANGED,
                        level=ChangeLevel.PATCH,
                        path=f"{base_path}.{meta_key}",
                        message=msg,
                        old_value=old_meta,
                        new_value=new_meta,
                    )
                    logger.debug("Detected column meta change: %s", msg)
                    changes.append(change)

        return changes

    # -------------------------------------------------------------------------
    # Blocks
    # -------------------------------------------------------------------------

    def _diff_blocks(
        self,
        sheet_path_prefix: str,
        old_blocks: Optional[Dict[str, Any]],
        new_blocks: Optional[Dict[str, Any]],
    ) -> List[SchemaChange]:
        changes: List[SchemaChange] = []
        if old_blocks is None and new_blocks is None:
            return changes

        if old_blocks != new_blocks:
            path = f"{sheet_path_prefix}.blocks"
            msg = f"Blocks changed in sheet '{sheet_path_prefix}'"
            # blocks는 대시보드/요약 블록 위치에 영향을 주므로 MINOR로 간주
            change = SchemaChange(
                change_type=ChangeType.BLOCKS_CHANGED,
                level=ChangeLevel.MINOR,
                path=path,
                message=msg,
                old_value=old_blocks,
                new_value=new_blocks,
            )
            logger.debug("Detected blocks change for sheet '%s'", sheet_path_prefix)
            changes.append(change)
        return changes
