import argparse
import logging
from pathlib import Path

from tools.schema.sheets_introspector import SheetsIntrospector
from tools.schema.schema_generator import SchemaGenerator
from tools.schema.schema_validator import SchemaValidator
from tools.schema.schema_diff import SchemaDiffEngine
from tools.schema.schema_version_manager import SchemaVersionManager
from tools.schema.schema_impact import SchemaImpactInspector

from src.sheets.google_client import GoogleSheetsClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_sheet_configs(path: Path):
    import json
    return [type("SheetConfig", (), cfg) for cfg in json.loads(path.read_text())]


def run_schema_pipeline(
    project_root: Path,
    sheet_config_path: Path,
    credentials: Path,
    spreadsheet_id: str
):

    logger.info("=== ATS Schema Engine Pipeline Start ===")

    # 1) Load config
    sheet_configs = load_sheet_configs(sheet_config_path)
    logger.info(f"Loaded {len(sheet_configs)} sheet configs")

    # 2) Google Client 초기화
    client = GoogleSheetsClient(
        credentials_path=str(credentials),
        spreadsheet_id=spreadsheet_id
    )

    # 3) Introspect
    introspector = SheetsIntrospector(client)
    raw_schema = introspector.introspect(sheet_configs)

    # 4) Generate schema
    generator = SchemaGenerator()
    master_schema = generator.generate(raw_schema)

    # 5) Validate
    validator = SchemaValidator()
    validator.validate(master_schema)

    # 6) Diff
    manager = SchemaVersionManager(project_root=project_root)
    diff_engine = SchemaDiffEngine()
    diff_result = diff_engine.compare(manager.load_latest_schema(), master_schema)

    # 7) Version update
    updated_schema_path = manager.update_version(master_schema, diff_result)

    # 8) Impact analysis
    inspector = SchemaImpactInspector(project_root=project_root)
    impact_report_path = inspector.generate_report(diff_result)

    logger.info(f"Schema updated at: {updated_schema_path}")
    logger.info(f"Impact report generated: {impact_report_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=str, default=".")
    parser.add_argument("--sheet-config", type=str, required=True)
    parser.add_argument("--credentials", type=str, required=True)
    parser.add_argument("--spreadsheet-id", type=str, required=True)   # ★ 추가된 부분

    args = parser.parse_args()

    run_schema_pipeline(
        project_root=Path(args.project_root).resolve(),
        sheet_config_path=Path(args.sheet_config).resolve(),
        credentials=Path(args.credentials).resolve(),
        spreadsheet_id=args.spreadsheet_id,
    )


if __name__ == "__main__":
    main()
