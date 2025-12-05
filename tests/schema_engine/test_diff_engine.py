# tests/schema_engine/test_diff_engine.py

from tools.schema.diff_engine_v2 import SchemaDiffEngine, ChangeLevel

def test_diff_engine_column_added():
    old = {
        "version": "1.0.0",
        "sheets": {
            "Test": {
                "name": "Test",
                "type": "table",
                "row_start": 2,
                "columns": [
                    {"col": "A", "name": "Ticker", "python_key": "ticker", "type": "string"},
                ]
            }
        }
    }

    new = {
        "version": "1.0.0",
        "sheets": {
            "Test": {
                "name": "Test",
                "type": "table",
                "row_start": 2,
                "columns": [
                    {"col": "A", "name": "Ticker", "python_key": "ticker", "type": "string"},
                    {"col": "B", "name": "Qty", "python_key": "qty", "type": "number"},
                ]
            }
        }
    }

    diff = SchemaDiffEngine().diff(old, new)
    assert diff.level == ChangeLevel.MINOR
    assert len(diff.changes) >= 1
