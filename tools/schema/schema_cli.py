"""
schema_cli.py

ATS Schema Engine Command-Line Pipeline (Integrated)

This CLI orchestrates the entire schema pipeline:

1. Load project config + sheet configs
2. Sheets Introspector → Raw Metadata
3. Schema Generator → Master Schema Draft
4. Schema Validator → Validate Schema
5. Load Old Schema → Diff Engine → SchemaDiffResult
6. Version Manager → Save new schema + schema history + diff summary
7. Impact Inspector → Impact Report

This CLI DOES NOT depend on Google APIs directly; it depends on a SheetsClient
interface (GoogleSheetsClient implementation resides in src/sheets/google_client.py).

"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import List

# --- Import ATS Schema Engine Components ---
from tools.schema.sheets_introspector import SheetsIntrospector, SheetConfig
from tools.schema.schema_generator import SchemaGenerator, GeneratorConfig
from tools.schema.schema_validator import SchemaValidator, SchemaValidationError
from tools.schema.diff_engine_v2 import SchemaDiffEngine
from tools.schema.schema_version_manager import SchemaVersionManager
from tools.schema.schema_impact_inspector import SchemaImpactInspector

# --- Sheets Client Implementation ---
# 실제 구현: src/sheets/google_client.py
from src.sheets.google_client import GoogleSheetsClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Helper: Load Sheet Config list
# -----------------------------------------------------------------------------

def load_sheet_configs(config_path: Path) -> List[SheetConfig]:
    """
    Load sheet config JSON from file:
    Example file:
    [
        {"name":"Position", "header_row":42, "data_start_row_hint":43},
        {"name":"DT_Report", "header_row":1, "data_start_row_hint":2}
    ]
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Sheet config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    configs = []
    for item in raw:
        configs.append(
            SheetConfig(
                name=item["name"],
                header_row=item.get("header_row", 1),
                data_start_row_hint=item.get("data_start_row_hint", None),
                max_columns=item.get("max_columns", 40),
                sample_row_count=item.get("sample_row_count", 20),
            )
        )
    return configs


# -----------------------------------------------------------------------------
# CLI Pipeline Logic
# -----------------------------------------------------------------------------

def run_schema_pipeline(
    project_root: Path,
    sheet_config_path: Path,
    google_credentials: Path,
) -> None:
    """
    Execute the entire schema engine pipeline.
    """

    logger.info("=== ATS Schema Engine Pipeline Start ===")

    # 1) Load sheet configs
    sheet_configs = load_sheet_configs(sheet_config_path)
    logger.info("Loaded %d sheet configs", len(sheet_configs))

    # 2) Init SheetsClient
    client = GoogleSheetsClient(credentials_path=str(google_credentials))

    # 3) Introspector
    introspector = SheetsIntrospector(client)
    raw_schema = introspector.introspect(sheet_configs)
    logger.info("RawMetadata extracted from Google Sheets")

    # 4) Generator
    generator = SchemaGenerator(config=GeneratorConfig())
    new_schema = generator.generate(raw_schema)
    logger.info("Master Schema generated")

    # 5) Validator
    validator = SchemaValidator()
    try:
        validator.validate(new_schema)
    except SchemaValidationError as exc:
        logger.error("Schema validation FAILED: %s", exc)
        raise

    logger.info("Master Schema validated successfully")

    # 6) Load Old Schema for Diff
    schema_file = project_root / "schemas" / "auto_trading_system.schema.json"
    if schema_file.exists():
        with schema_file.open("r", encoding="utf-8") as f:
            old_schema = json.load(f)
        logger.info("Loaded old schema for diff comparison")
    else:
        old_schema = {"version": "0.0.0", "sheets": {}}
        logger.warning("Old schema not found. Using empty base schema for diff.")

    # 7) Diff Engine
    diff_engine = SchemaDiffEngine()
    diff_result = diff_engine.diff(old_schema, new_schema)
    logger.info(
        "Diff Engine completed. Total changes=%d, Level=%s",
        len(diff_result.changes),
        diff_result.level.name,
    )

    # 8) Version Manager
    version_manager = SchemaVersionManager(project_root=project_root)
    versioning_result = version_manager.apply_versioning(
        current_schema=new_schema,
        diff_result=diff_result,
        current_version_str=old_schema.get("version"),
    )
    logger.info(
        "Version Manager: %s → %s",
        versioning_result.old_version,
        versioning_result.new_version,
    )

    # 9) Impact Inspector
    inspector = SchemaImpactInspector(project_root)
    impact_report = inspector.analyze(diff_result)
    report_path = inspector.write_markdown_report(impact_report)

    logger.info("Impact Report written to %s", report_path)
    logger.info("=== ATS Schema Engine Pipeline Completed ===")


# -----------------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ATS Schema Engine Pipeline")
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Project root directory",
    )
    parser.add_argument(
        "--sheet-config",
        type=str,
        required=True,
        help="Path to JSON file listing sheet configs",
    )
    parser.add_argument(
        "--credentials",
        type=str,
        required=True,
        help="Google Sheets API credential JSON path",
    )

    args = parser.parse_args()
    run_schema_pipeline(
        project_root=Path(args.project_root).resolve(),
        sheet_config_path=Path(args.sheet_config).resolve(),
        google_credentials=Path(args.credentials).resolve(),
    )


if __name__ == "__main__":
    main()
