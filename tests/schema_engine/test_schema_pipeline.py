# tests/schema_engine/test_schema_pipeline.py

import json
from pathlib import Path
from tools.schema.schema_cli import run_schema_pipeline

def test_schema_pipeline_end_to_end(tmp_path, monkeypatch):
    """
    전체 파이프라인을 테스트.
    schema_cli.py 내부에서 import된 GoogleSheetsClient를 정확히 Dummy로 대체.
    """

    # Dummy Google Sheets Client
    class DummySheetsClient:
        def __init__(self, *args, **kwargs):
            pass
        def read_range(self, sheet, range_a1):
            return [["Ticker", "Qty"], ["005930", 10]]

    # 핵심: schema_cli 내부 GoogleSheetsClient를 대체해야 함
    monkeypatch.setattr(
        "tools.schema.schema_cli.GoogleSheetsClient",
        DummySheetsClient
    )

    # sheet_config 생성
    config_path = tmp_path / "sheet_config.json"
    config_path.write_text(json.dumps([
        {
            "name": "Position",
            "header_row": 1,
            "data_start_row_hint": 2,
            "max_columns": 5,
            "sample_row_count": 5
        }
    ]))

    # 스키마 디렉토리 구조 생성
    (tmp_path / "schemas" / "history").mkdir(parents=True)
    (tmp_path / "reports" / "schema").mkdir(parents=True)

    # 파이프라인 실행
    run_schema_pipeline(
        project_root=tmp_path,
        sheet_config_path=config_path,
        google_credentials=tmp_path / "dummy.json"
    )

    # 새 스키마 파일 생성 확인
    assert (tmp_path / "schemas" / "auto_trading_system.schema.json").exists()

    # 버전 히스토리 생성 확인
    assert len(list((tmp_path / "schemas" / "history").glob("*.json"))) >= 1

    # Impact Report 생성 확인
    assert len(list((tmp_path / "reports" / "schema").glob("impact_report_*.md"))) >= 1
