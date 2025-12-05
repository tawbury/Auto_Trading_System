# tests/schema_engine/test_schema_validator.py

import pytest
from tools.schema.schema_validator import SchemaValidator, SchemaValidationError

def test_validator_ok():
    validator = SchemaValidator()

    valid_schema = {
        "project": "ATS",
        "version": "0.0.0",
        "sheets": {
            "TestSheet": {
                "name": "TestSheet",
                "type": "table",
                "row_start": 2,
                "columns": [
                    {"col": "A", "name": "Ticker", "python_key": "ticker", "type": "string"},
                    {"col": "B", "name": "Qty", "python_key": "qty", "type": "number"},
                ]
            }
        }
    }

    out = validator.validate(valid_schema)
    assert out is valid_schema  # 변환 없이 그대로

def test_validator_duplicate_python_key():
    validator = SchemaValidator()
    schema = {
        "project": "ATS",
        "version": "0.0.0",
        "sheets": {
            "Sheet": {
                "name": "Sheet",
                "type": "table",
                "row_start": 2,
                "columns": [
                    {"col": "A", "name": "Ticker", "python_key": "ticker", "type": "string"},
                    {"col": "B", "name": "Ticker2", "python_key": "ticker", "type": "string"},
                ]
            }
        }
    }
    with pytest.raises(SchemaValidationError):
        validator.validate(schema)
