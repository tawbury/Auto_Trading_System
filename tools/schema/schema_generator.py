"""
schema_generator.py

Schema Generator for ATS Schema Engine.

Responsibilities
----------------
- Convert RawSchemaMeta (from SheetsIntrospector) into a normalized Master Schema.
- Apply naming conventions and canonical field structure based on ATS architecture.
- Fill required schema sections:
    - project
    - version (default: "0.0.0" until VersionManager assigns one)
    - sheets: each with fields:
        - type (inferred or externally supplied; default "table")
        - row_start
        - columns: col / name / python_key / type
        - blocks (not inferred here; handled by block config or external mapping)
- Ensure compatibility with:
    - SchemaValidator
    - Diff Engine
    - Version Manager

Design Notes
------------
- Blocks are NOT inferred automatically from Google Sheets — they require either:
    - external configuration,
    - manually defined mapping,
    - or a dedicated block introspector.
  This generator supports injecting block definitions optionally.

- The generator does NOT write files. It only returns a dict suitable for JSON dump.
- Writing to /schemas/*.json is handled by the version manager.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .sheets_introspector import RawSchemaMeta, RawSheetMeta, RawColumnMeta

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Configuration object (optional)
# -----------------------------------------------------------------------------


@dataclass
class GeneratorConfig:
    """
    Optional configuration for SchemaGenerator.

    Attributes
    ----------
    project_name:
        Name stored under schema["project"]
    default_sheet_type:
        Default sheet type for sheets without explicit type (e.g. "table")
    blocks_mapping:
        Optional mapping:
            {
                "Position": {
                    "Summary": { "total_equity": "B4", ... },
                    "Constraints": {...}
                },
                "History": {...}
            }
        If provided, the generator injects these blocks into the schema.
    """

    project_name: str = "auto_trading_system"
    default_sheet_type: str = "table"
    blocks_mapping: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None


# -----------------------------------------------------------------------------
# Schema Generator
# -----------------------------------------------------------------------------


class SchemaGenerator:
    """
    Convert RawSchemaMeta into a normalized Master Schema.

    Usage:
    ------
        raw_meta = introspector.introspect(sheet_configs)
        generator = SchemaGenerator(config=GeneratorConfig())
        master_schema = generator.generate(raw_meta)
    """

    def __init__(self, config: Optional[GeneratorConfig] = None) -> None:
        self.config = config or GeneratorConfig()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def generate(self, raw_meta: RawSchemaMeta) -> Dict[str, Any]:
        """
        Generate Master Schema from raw metadata.

        Parameters
        ----------
        raw_meta: RawSchemaMeta
            Raw structure from SheetsIntrospector.

        Returns
        -------
        schema: Dict[str, Any]
            Normalized Master Schema JSON structure.
        """
        logger.info("Generating Master Schema from raw metadata")

        schema: Dict[str, Any] = {
            "project": self.config.project_name,
            "version": "0.0.0",  # Will be updated by the Version Manager
            "sheets": {},
        }

        for sheet_name, sheet_meta in raw_meta.sheets.items():
            schema["sheets"][sheet_name] = self._generate_single_sheet(sheet_meta)

        return schema

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _generate_single_sheet(self, sheet: RawSheetMeta) -> Dict[str, Any]:
        """
        Convert RawSheetMeta to normalized schema for a single sheet.
        """
        logger.debug("Generating schema for sheet '%s'", sheet.name)

        sheet_def: Dict[str, Any] = {
            "name": sheet.name,
            "type": self.config.default_sheet_type,
            "row_start": sheet.row_start,
            "columns": [],
        }

        # Columns
        for col_meta in sheet.columns:
            col_def = self._generate_column(col_meta)
            sheet_def["columns"].append(col_def)

        # Blocks (optional injection)
        if self.config.blocks_mapping and sheet.name in self.config.blocks_mapping:
            sheet_def["blocks"] = self.config.blocks_mapping[sheet.name]

        return sheet_def

    def _generate_column(self, col: RawColumnMeta) -> Dict[str, Any]:
        """
        Convert RawColumnMeta to normalized column schema.
        """
        return {
            "col": col.col,
            "name": col.name,
            "python_key": col.python_key,
            "type": col.inferred_type,
        }
