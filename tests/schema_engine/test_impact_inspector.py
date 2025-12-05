# tests/schema_engine/test_impact_inspector.py

from pathlib import Path
from tools.schema.schema_impact_inspector import SchemaImpactInspector
from tools.schema.diff_engine_v2 import SchemaDiffResult, SchemaChange, ChangeType, ChangeLevel

def test_impact_inspector_position(tmp_path):
    inspector = SchemaImpactInspector(project_root=tmp_path)

    diff = SchemaDiffResult(
        changes=[
            SchemaChange(
                path="Position.columns[Qty]",
                change_type=ChangeType.COLUMN_TYPE_CHANGED,
                level=ChangeLevel.MAJOR,
                message="Qty type changed"
            )
        ]
    )

    report = inspector.analyze(diff)
    assert len(report.targets) >= 1
