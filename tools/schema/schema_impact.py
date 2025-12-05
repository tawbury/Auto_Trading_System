"""
SchemaImpactInspector
---------------------
스키마 변경(diff)에 따른 시스템 영향도 분석 및 Markdown 보고서 생성기.
"""

from pathlib import Path
from datetime import datetime
from typing import List

from tools.schema.schema_diff import (
    SchemaDiffResult,
    SchemaChange,
    ChangeLevel,
    ChangeType,
)


class SchemaImpactInspector:

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.reports_dir = project_root / "reports" / "schema"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # Impact Evaluation Logic
    # ---------------------------------------------------------
    def evaluate_change_impact(self, change: SchemaChange) -> str:
        """
        변경 유형(ChangeType)에 따라 영향도를 시나리오 형태로 분석.
        """

        if change.change_type == ChangeType.SHEET_ADDED:
            return f"- 신규 시트 추가: 시스템은 해당 시트를 읽기 위한 로직이 필요합니다."

        if change.change_type == ChangeType.SHEET_REMOVED:
            return f"- 시트 삭제: 시스템에서 이 시트를 참조하는 모든 코드가 오류를 발생할 수 있습니다."

        if change.change_type == ChangeType.COLUMN_ADDED:
            return f"- 신규 컬럼 추가: DB 매핑/모델에서 해당 필드 반영 여부를 점검해야 합니다."

        if change.change_type == ChangeType.COLUMN_REMOVED:
            return f"- 컬럼 삭제: 이 컬럼을 사용하는 로직에서 KeyError 또는 누락 오류 가능성이 있습니다."

        if change.change_type == ChangeType.COLUMN_TYPE_CHANGED:
            return f"- 컬럼 정의 변경: 데이터 타입 mismatch 또는 계산 로직 수정이 필요합니다."

        return "- 영향 분석 불가: 정의되지 않은 유형."

    # ---------------------------------------------------------
    # Build Markdown Report
    # ---------------------------------------------------------
    def build_markdown(self, diff: SchemaDiffResult) -> str:
        lines: List[str] = []

        lines.append("# ATS Schema Impact Report\n")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"Overall Change Level: **{diff.level.name}**\n")
        lines.append("---\n")

        if not diff.changes:
            lines.append("### No schema changes detected.\n")
            return "\n".join(lines)

        lines.append("## Change Details\n")

        for change in diff.changes:
            impact_text = self.evaluate_change_impact(change)

            lines.append(f"### {change.message}\n")
            lines.append(f"- Path: `{change.path}`")
            lines.append(f"- Change Type: **{change.change_type.name}**")
            lines.append(f"- Change Level: **{change.level.name}**")
            lines.append(f"- Impact:\n  {impact_text}\n")
            lines.append("---")

        return "\n".join(lines)

    # ---------------------------------------------------------
    # Public API: Generate Report File
    # ---------------------------------------------------------
    def generate_report(self, diff: SchemaDiffResult) -> Path:
        """
        diff 기반으로 영향도 분석 후 Markdown 파일 생성.
        """

        md_text = self.build_markdown(diff)

        file_name = f"impact_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        output_path = self.reports_dir / file_name

        output_path.write_text(md_text, encoding="utf-8")

        return output_path
