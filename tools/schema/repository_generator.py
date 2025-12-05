"""
Repository Generator
--------------------
Master Schema(auto_trading_system.schema.json)를 기반으로
시트별 Repository 코드를 자동 생성한다.

사용 예:
    python -m tools.schema.repository_generator --project-root . 

옵션:
    --project-root : 프로젝트 루트 (기본값: 현재 디렉토리)
    --schema-path  : 스키마 JSON 경로 (기본값: schemas/auto_trading_system.schema.json)
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class SheetSchema:
    name: str
    header_row: int
    data_start_row: int
    columns: List[str]


class RepositoryGenerator:
    def __init__(self, project_root: Path, schema_path: Path) -> None:
        self.project_root = project_root
        self.schema_path = schema_path
        self.output_dir = project_root / "src" / "repositories"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------
    # Schema 로딩 및 정규화
    # -----------------------------
    def load_schema(self) -> Dict[str, Any]:
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        return json.loads(self.schema_path.read_text(encoding="utf-8"))

    @staticmethod
    def _normalize_columns(cols_raw: Any) -> List[str]:
        """
        컬럼 정의를 헤더 이름 리스트로 정규화.
        - dict: {name: {...}} 또는 {name: "A"} 형태 → key 목록 사용
        - list: [{"name": "Symbol", ...}, ...] 형태 → name 필드 사용
        """
        result: List[str] = []

        if isinstance(cols_raw, dict):
            # key 기반
            for key in cols_raw.keys():
                result.append(str(key))
        elif isinstance(cols_raw, list):
            for item in cols_raw:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                if not name:
                    # name이 없으면 column letter라도 써준다
                    name = item.get("column")
                if not name:
                    continue
                result.append(str(name))
        else:
            # 예상치 못한 타입은 무시
            pass

        return result

    @staticmethod
    def _to_python_field_name(header: str) -> str:
        """
        헤더 문자열을 파이썬 변수명(snake_case)으로 변환.
        예:
            "Symbol" → "symbol"
            "Avg_Price(Current_Currency)" → "avg_price_current_currency"
        """
        s = header.lower()
        s = re.sub(r"[^a-z0-9]+", "_", s)
        s = s.strip("_")
        if not s:
            s = "col"
        return s

    @staticmethod
    def _to_class_name(sheet_name: str, suffix: str) -> str:
        """
        시트 이름을 PascalCase + suffix 형태로 변환.
        예:
            "Position"   → "PositionRow" / "PositionRepository"
            "T_Ledger"   → "TLedgerRow" / "TLedgerRepository"
        """
        parts = re.split(r"[^A-Za-z0-9]+", sheet_name)
        parts = [p for p in parts if p]
        base = "".join(p.capitalize() for p in parts) or "Sheet"
        return base + suffix

    def extract_sheet_schemas(self, schema: Dict[str, Any]) -> List[SheetSchema]:
        sheets = schema.get("sheets", {})
        results: List[SheetSchema] = []

        for sheet_name, meta in sheets.items():
            # blocks만 있는 대시보드형 시트(R_Dash 등)는 스킵
            if "columns" not in meta or "row_start" not in meta:
                continue

            header_row = int(meta.get("header_row", meta["row_start"] - 1))
            data_start_row = int(meta.get("row_start"))

            cols_raw = meta.get("columns", {})
            columns = self._normalize_columns(cols_raw)

            if not columns:
                continue

            results.append(
                SheetSchema(
                    name=sheet_name,
                    header_row=header_row,
                    data_start_row=data_start_row,
                    columns=columns,
                )
            )

        return results

    # -----------------------------
    # 코드 생성
    # -----------------------------
    def generate_repository_code(self, sheet: SheetSchema) -> str:
        """
        한 시트에 대한 Repository 코드 문자열 생성.
        """
        row_class_name = self._to_class_name(sheet.name, "Row")
        repo_class_name = self._to_class_name(sheet.name, "Repository")
        module_doc = f'"""Repository for {sheet.name} sheet (auto-generated)."""\n'

        # dataclass 필드 정의
        field_lines = []
        for col_name in sheet.columns:
            field_name = self._to_python_field_name(col_name)
            field_lines.append(f"    {field_name}: str | None = None")

        dataclass_block = "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from dataclasses import dataclass",
                "from typing import List, Any",
                "",
                "from src.sheets.google_client import GoogleSheetsClient",
                "from src.repositories.base import BaseSheetRepository",
                "",
                "",
                f"@dataclass",
                f"class {row_class_name}:",
                *([*field_lines] or ["    pass"]),
                "",
            ]
        )

        # parse_row 구현 (단순 매핑)
        parse_lines = []
        for idx, col_name in enumerate(sheet.columns):
            field_name = self._to_python_field_name(col_name)
            parse_lines.append(
                f"        {field_name}=row[{idx}] if len(row) > {idx} else None,"
            )

        repo_block = "\n".join(
            [
                f"class {repo_class_name}(BaseSheetRepository[{row_class_name}]):",
                f'    """',
                f"    {sheet.name} 시트용 Repository (자동 생성 코드).",
                f"    - header_row: {sheet.header_row}",
                f"    - data_start_row: {sheet.data_start_row}",
                f'    - columns: {", ".join(sheet.columns)}',
                f'    """',
                "",
                "    def __init__(self, client: GoogleSheetsClient) -> None:",
                f'        super().__init__(',
                f'            client=client,',
                f'            sheet_name="{sheet.name}",',
                f"            header_row={sheet.header_row},",
                f"            data_start_row={sheet.data_start_row},",
                f"            columns={sheet.columns!r},",
                "        )",
                "",
                "    def parse_row(self, row: List[Any]) -> " + row_class_name + ":",
                f"        return {row_class_name}(",
                *parse_lines,
                "        )",
                "",
            ]
        )

        return module_doc + "\n" + dataclass_block + "\n" + repo_block

    def write_repository_file(self, sheet: SheetSchema) -> Path:
        """
        한 시트에 대한 Repository 파일을 생성/덮어쓰기.
        """
        file_name = f"{sheet.name.lower()}_repository.py"
        output_path = self.output_dir / file_name

        code = self.generate_repository_code(sheet)
        output_path.write_text(code, encoding="utf-8")

        return output_path

    def run(self) -> None:
        schema = self.load_schema()
        sheet_schemas = self.extract_sheet_schemas(schema)

        if not sheet_schemas:
            print("No tabular sheets found in schema. Nothing to generate.")
            return

        for sheet in sheet_schemas:
            path = self.write_repository_file(sheet)
            print(f"[RepositoryGenerator] Generated: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ATS Repository Generator")
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Project root path (default: current directory)",
    )
    parser.add_argument(
        "--schema-path",
        type=str,
        default=None,
        help="Schema JSON path (default: schemas/auto_trading_system.schema.json)",
    )

    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    schema_path = (
        Path(args.schema_path).resolve()
        if args.schema_path
        else project_root / "schemas" / "auto_trading_system.schema.json"
    )

    generator = RepositoryGenerator(project_root=project_root, schema_path=schema_path)
    generator.run()


if __name__ == "__main__":
    main()
