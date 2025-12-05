"""
sheets_introspector.py

Sheets Introspector for ATS Schema Engine.

Responsibilities
----------------
- Connect to a Google Sheets client (or compatible sheets client).
- Read header rows and sample data from configured sheets.
- Infer:
    - row_start (first data row)
    - columns:
        - col (A, B, C ...)
        - name (header text)
        - python_key (snake_case key)
        - type (inferred from sample values: number/string/date/bool)
- Produce a "raw metadata" structure that can be fed into the Schema Generator.

Design Notes
------------
- This module does NOT write files. It only returns Python dicts / dataclasses.
- It depends on an abstract sheets client that provides:
    - read_range(sheet_name: str, range_a1: str) -> List[List[Any]]
  The concrete implementation (GoogleSheetsClient) lives in src/sheets.
- The actual mapping from `RawSchema` -> Master Schema JSON은 schema_generator가 담당한다.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Sheets client abstraction
# -----------------------------------------------------------------------------


class SheetsClientProtocol(Protocol):
    """
    Minimal protocol for a sheets client.

    A concrete implementation (e.g. GoogleSheetsClient) MUST implement at least:

        def read_range(self, sheet_name: str, range_a1: str) -> List[List[Any]]:
            ...

    - `sheet_name`는 Google 시트의 탭 이름
    - `range_a1`은 'A1:Z10' 형태의 A1 표기법
    """

    def read_range(self, sheet_name: str, range_a1: str) -> List[List[Any]]:
        ...


# -----------------------------------------------------------------------------
# Data model for raw metadata
# -----------------------------------------------------------------------------


@dataclass
class SheetConfig:
    """
    Configuration for a sheet to introspect.

    Attributes
    ----------
    name:
        Google Sheet tab name (e.g. "Position", "DT_Report").
    header_row:
        Header row index (1-based). Default: 1.
    data_start_row_hint:
        Expected first data row (1-based). If None, introspector will try to detect
        the first non-empty row after header_row.
    max_columns:
        Max columns to scan (e.g. 30 -> up to AD). If header row is shorter,
        scan stops at the last non-empty cell.
    sample_row_count:
        Number of sample data rows to read to infer types.
    """

    name: str
    header_row: int = 1
    data_start_row_hint: Optional[int] = None
    max_columns: int = 40
    sample_row_count: int = 20


@dataclass
class RawColumnMeta:
    """
    Raw metadata for a single column.
    """
    col: str
    name: str
    python_key: str
    inferred_type: str
    samples: List[Any]


@dataclass
class RawSheetMeta:
    """
    Raw metadata for a sheet extracted via introspection.
    """
    name: str
    row_start: int
    columns: List[RawColumnMeta]


@dataclass
class RawSchemaMeta:
    """
    Aggregated raw schema for multiple sheets.
    """
    sheets: Dict[str, RawSheetMeta]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a plain dict suitable for JSON serialization or passing
        into the schema generator.
        """
        return {
            "sheets": {
                name: {
                    "name": sheet.name,
                    "row_start": sheet.row_start,
                    "columns": [
                        {
                            "col": col.col,
                            "name": col.name,
                            "python_key": col.python_key,
                            "type": col.inferred_type,
                            "samples": col.samples,
                        }
                        for col in sheet.columns
                    ],
                }
                for name, sheet in self.sheets.items()
            }
        }


# -----------------------------------------------------------------------------
# Introspector implementation
# -----------------------------------------------------------------------------


class SheetsIntrospectorError(Exception):
    """Raised when introspection fails for any reason."""


class SheetsIntrospector:
    """
    SheetsIntrospector reads header rows and sample data from a sheets client
    and produces RawSchemaMeta.

    Usage (high-level)
    ------------------
    client: SheetsClientProtocol = GoogleSheetsClient(...)
    introspector = SheetsIntrospector(client)
    raw_schema = introspector.introspect([
        SheetConfig(name="Position", header_row=42, data_start_row_hint=43),
        SheetConfig(name="DT_Report", header_row=1, data_start_row_hint=2),
    ])
    """

    def __init__(self, client: SheetsClientProtocol) -> None:
        self.client = client

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def introspect(self, sheet_configs: Iterable[SheetConfig]) -> RawSchemaMeta:
        """
        Introspect multiple sheets and return RawSchemaMeta.

        Parameters
        ----------
        sheet_configs:
            Iterable of SheetConfig objects specifying which sheets to scan.

        Returns
        -------
        RawSchemaMeta
        """
        sheets_meta: Dict[str, RawSheetMeta] = {}

        for config in sheet_configs:
            logger.info("Introspecting sheet '%s'", config.name)
            sheet_meta = self._introspect_single_sheet(config)
            sheets_meta[config.name] = sheet_meta
            logger.debug(
                "Finished sheet '%s': row_start=%d, columns=%d",
                config.name,
                sheet_meta.row_start,
                len(sheet_meta.columns),
            )

        return RawSchemaMeta(sheets=sheets_meta)

    # -------------------------------------------------------------------------
    # Single sheet introspection
    # -------------------------------------------------------------------------

    def _introspect_single_sheet(self, config: SheetConfig) -> RawSheetMeta:
        # 1) Read header row
        header_range = self._build_header_range(config)
        header_rows = self.client.read_range(config.name, header_range)

        if not header_rows or not header_rows[0]:
            raise SheetsIntrospectorError(
                f"Header row appears empty for sheet '{config.name}' "
                f"(range={header_range})"
            )

        header_values = header_rows[0]
        logger.debug("Header values for '%s': %s", config.name, header_values)

        # 2) Detect effective last column index (based on header non-empty cells)
        last_col_index = self._detect_last_header_col_index(header_values)
        if last_col_index < 0:
            raise SheetsIntrospectorError(
                f"No non-empty header cells found for sheet '{config.name}' "
                f"(range={header_range})"
            )

        # 3) Calculate row_start
        row_start = (
            config.data_start_row_hint
            if config.data_start_row_hint is not None
            else config.header_row + 1
        )

        # 4) Read sample rows for type inference
        sample_range = self._build_sample_range(
            config,
            last_col_index=last_col_index,
            row_start=row_start,
        )
        sample_rows = self.client.read_range(config.name, sample_range)
        logger.debug(
            "Read %d sample row(s) for '%s' (range=%s)",
            len(sample_rows),
            config.name,
            sample_range,
        )

        # Normalize sample rows to fixed width
        normalized_samples = self._normalize_sample_rows(
            sample_rows,
            expected_cols=last_col_index + 1,
        )

        # 5) Build RawColumnMeta list
        columns_meta: List[RawColumnMeta] = []
        for idx in range(last_col_index + 1):
            col_letter = self._index_to_col_letter(idx)
            header_text = str(header_values[idx]).strip() if idx < len(header_values) else ""
            python_key = self._to_python_key(header_text, fallback=f"col_{col_letter.lower()}")

            # Collect samples for this column
            col_samples = [row[idx] for row in normalized_samples if idx < len(row)]
            inferred_type = self._infer_type(col_samples)

            col_meta = RawColumnMeta(
                col=col_letter,
                name=header_text,
                python_key=python_key,
                inferred_type=inferred_type,
                samples=col_samples,
            )
            columns_meta.append(col_meta)

        return RawSheetMeta(
            name=config.name,
            row_start=row_start,
            columns=columns_meta,
        )

    # -------------------------------------------------------------------------
    # Helpers: ranges, headers, samples
    # -------------------------------------------------------------------------

    def _build_header_range(self, config: SheetConfig) -> str:
        """
        Build A1 range string for the header row, e.g. "A1:AN1".
        """
        last_col_index = max(config.max_columns - 1, 0)
        last_col_letter = self._index_to_col_letter(last_col_index)
        return f"A{config.header_row}:{last_col_letter}{config.header_row}"

    def _build_sample_range(
        self,
        config: SheetConfig,
        last_col_index: int,
        row_start: int,
    ) -> str:
        """
        Build A1 range string for sample data rows.
        """
        last_col_letter = self._index_to_col_letter(last_col_index)
        row_end = row_start + max(config.sample_row_count - 1, 0)
        return f"A{row_start}:{last_col_letter}{row_end}"

    @staticmethod
    def _detect_last_header_col_index(header_values: List[Any]) -> int:
        """
        Detect the last non-empty header index.

        Returns
        -------
        Index (0-based) of the last non-empty cell, or -1 if all are empty.
        """
        last_idx = -1
        for idx, val in enumerate(header_values):
            if str(val).strip():
                last_idx = idx
        return last_idx

    @staticmethod
    def _normalize_sample_rows(
        rows: List[List[Any]],
        expected_cols: int,
    ) -> List[List[Any]]:
        """
        Normalize rows to a fixed number of columns.

        - Shorter rows are padded with None.
        - Longer rows are truncated.
        """
        normalized: List[List[Any]] = []
        for row in rows:
            if len(row) < expected_cols:
                row = row + [None] * (expected_cols - len(row))
            elif len(row) > expected_cols:
                row = row[:expected_cols]
            normalized.append(row)
        return normalized

    # -------------------------------------------------------------------------
    # Helpers: column index <-> letter
    # -------------------------------------------------------------------------

    @staticmethod
    def _index_to_col_letter(index: int) -> str:
        """
        Convert 0-based column index to Excel/Sheets-style column letter.
        Example:
            0 -> A
            25 -> Z
            26 -> AA
        """
        if index < 0:
            raise ValueError("Column index must be non-negative")
        result = []
        i = index
        while True:
            i, rem = divmod(i, 26)
            result.append(chr(ord("A") + rem))
            if i == 0:
                break
            i -= 1
        return "".join(reversed(result))

    # -------------------------------------------------------------------------
    # Helpers: python_key, type inference
    # -------------------------------------------------------------------------

    @staticmethod
    def _to_python_key(header: str, fallback: str) -> str:
        """
        Convert header text into a snake_case Python key.

        Examples:
            "Total Equity" -> "total_equity"
            "PnL %" -> "pnl_pct"
        """
        text = header.strip()
        if not text:
            return fallback

        # Basic normalization
        text = text.replace("%", "pct")
        text = re.sub(r"[^\w]+", "_", text)  # non-word -> underscore
        text = re.sub(r"_+", "_", text)
        text = text.strip("_").lower()
        return text or fallback

    def _infer_type(self, samples: List[Any]) -> str:
        """
        Infer a simple type from sample values.

        Returns one of: "number", "date", "bool", "string"
        """
        # Filter out empty samples
        non_empty = [s for s in samples if s not in (None, "", " ")]
        if not non_empty:
            # Default to string if no samples
            return "string"

        # Try boolean
        if self._looks_like_bool(non_empty):
            return "bool"

        # Try number
        if self._looks_like_number(non_empty):
            return "number"

        # Try date (very naive; for real use, consider parsing with dateutil)
        if self._looks_like_date(non_empty):
            return "date"

        # Fallback
        return "string"

    @staticmethod
    def _looks_like_bool(values: List[Any]) -> bool:
        truthy = {"true", "false", "yes", "no", "y", "n"}
        for v in values:
            s = str(v).strip().lower()
            if s not in truthy:
                return False
        return True

    @staticmethod
    def _looks_like_number(values: List[Any]) -> bool:
        for v in values:
            if isinstance(v, (int, float)):
                continue
            s = str(v).strip().replace(",", "")
            if not s:
                continue
            try:
                float(s)
            except ValueError:
                return False
        return True

    @staticmethod
    def _looks_like_date(values: List[Any]) -> bool:
        """
        Very lightweight check: looks for patterns like 'YYYY-MM-DD' or 'YYYY/MM/DD'.
        This is intentionally naive to avoid heavy dependencies.
        """
        pattern = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$")
        for v in values:
            if isinstance(v, (int, float)):
                # In Google Sheets, dates might come as serial numbers.
                # 여기서는 단순화를 위해 숫자 date는 타입 판별에서 제외한다.
                return False
            s = str(v).strip()
            if not pattern.match(s):
                return False
        return True
