# tests/schema_engine/test_schema_generator.py

from tools.schema.schema_generator import SchemaGenerator, GeneratorConfig
from tools.schema.sheets_introspector import RawSchemaMeta, RawSheetMeta, RawColumnMeta

def test_schema_generator_basic():
    raw = RawSchemaMeta(
        sheets={
            "TestSheet": RawSheetMeta(
                name="TestSheet",
                row_start=2,
                columns=[
                    RawColumnMeta("A", "Ticker", "ticker", "string", ["005930"]),
                    RawColumnMeta("B", "Qty", "qty", "number", [10]),
                ]
            )
        }
    )

    generator = SchemaGenerator(GeneratorConfig(project_name="ATS"))
    schema = generator.generate(raw)

    assert schema["project"] == "ATS"
    assert schema["version"] == "0.0.0"
    assert "TestSheet" in schema["sheets"]

    sheet = schema["sheets"]["TestSheet"]
    assert sheet["row_start"] == 2
    assert len(sheet["columns"]) == 2
