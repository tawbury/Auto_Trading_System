# tests/schema_engine/test_version_manager.py

from pathlib import Path
from tools.schema.schema_version_manager import SchemaVersionManager
from tools.schema.diff_engine_v2 import SchemaDiffResult, SchemaChange, ChangeType, ChangeLevel

def test_version_bump(tmp_path):
    manager = SchemaVersionManager(project_root=tmp_path)

    # MINOR 수준 변화를 가진 Change 객체 1개 생성
    change = SchemaChange(
        path="TestSheet.columns[Qty]",
        change_type=ChangeType.COLUMN_ADDED,
        level=ChangeLevel.MINOR,
        message="Test minor change"
    )

    diff = SchemaDiffResult(changes=[change])

    result = manager.apply_versioning(
        current_schema={"project": "ATS", "version": "1.0.0", "sheets": {}},
        diff_result=diff,
        current_version_str="1.0.0"
    )

    assert result.new_version == "1.1.0"
    assert (tmp_path / "schemas" / "auto_trading_system.schema.json").exists()
