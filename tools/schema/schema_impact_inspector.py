"""
schema_impact_inspector.py

Schema Impact Inspector for ATS Schema Engine.

Responsibilities:
- Analyze SchemaDiffResult and infer which ATS modules/files are potentially impacted.
- Produce a structured ImpactReport including:
    - impacted modules/files
    - impact category (repository / engine / sheets_adapter / dashboard / other)
    - reason and related schema change
- Optionally emit a human-readable markdown report under /reports/schema.

This module is intentionally heuristic:
- It uses sheet names and change types to map to impacted modules.
- Mapping rules are centralized and can be adjusted per project.

Assumptions:
- Project structure follows the Project_Folder_Convention:
    - src/sheets/
    - src/engine/
    - src/brokers/ (not used here but could be extended)
    - reports/schema/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Iterable, Optional, Set

from .diff_engine_v2 import (
    SchemaDiffResult,
    SchemaChange,
    ChangeType,
    ChangeLevel,
)

logger = logging.getLogger(__name__)


class ImpactCategory(Enum):
    """High-level category of impacted module."""
    REPOSITORY = "repository"
    ENGINE = "engine"
    SHEETS_ADAPTER = "sheets_adapter"
    DASHBOARD = "dashboard"
    RISK = "risk"
    STRATEGY = "strategy"
    OTHER = "other"


@dataclass
class ImpactTarget:
    """
    Represents a single impacted target (e.g., Python module file path).
    """
    category: ImpactCategory
    file_path: Path
    reason: str
    related_changes: List[SchemaChange] = field(default_factory=list)

    def add_change(self, change: SchemaChange) -> None:
        self.related_changes.append(change)


@dataclass
class ImpactReport:
    """
    Aggregated impact analysis result.
    """
    diff_level: ChangeLevel
    changes: List[SchemaChange]
    targets: List[ImpactTarget]

    @property
    def is_empty(self) -> bool:
        return not self.targets

    def targets_by_category(self) -> Dict[ImpactCategory, List[ImpactTarget]]:
        grouped: Dict[ImpactCategory, List[ImpactTarget]] = {}
        for target in self.targets:
            grouped.setdefault(target.category, []).append(target)
        return grouped


class SchemaImpactInspector:
    """
    SchemaImpactInspector analyzes a SchemaDiffResult and maps schema changes
    to impacted ATS modules/files based on configurable rules.

    It does NOT modify code. It only reports potential impact.
    """

    def __init__(
        self,
        project_root: Path,
        reports_dir: str = "reports/schema",
    ) -> None:
        self.project_root = project_root
        self.reports_dir = project_root / reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(
            "SchemaImpactInspector initialized with project_root=%s, reports_dir=%s",
            self.project_root,
            self.reports_dir,
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def analyze(self, diff_result: SchemaDiffResult) -> ImpactReport:
        """
        Analyze diff_result and return an ImpactReport with impacted targets.

        The mapping uses sheet name + change type to infer affected modules.
        """
        logger.info("Starting impact analysis for diff level=%s", diff_result.level.name)

        if diff_result.is_empty():
            logger.info("No schema changes. Impact report will be empty.")
            return ImpactReport(diff_level=ChangeLevel.PATCH, changes=[], targets=[])

        # 1) Group changes by sheet (top-level path prefix)
        changes_by_sheet = self._group_changes_by_sheet(diff_result.changes)

        # 2) For each sheet, derive impacted targets
        targets_map: Dict[Path, ImpactTarget] = {}

        for sheet_name, sheet_changes in changes_by_sheet.items():
            sheet_targets = self._infer_targets_for_sheet(sheet_name, sheet_changes)
            for target in sheet_targets:
                # Consolidate by file_path + category
                key = (target.file_path, target.category)
                existing = targets_map.get(target.file_path)
                if existing and existing.category == target.category:
                    for ch in target.related_changes:
                        existing.add_change(ch)
                else:
                    targets_map[target.file_path] = target

        targets = list(targets_map.values())
        logger.info("Impact analysis completed: %d impacted target(s)", len(targets))

        return ImpactReport(
            diff_level=diff_result.level,
            changes=diff_result.changes,
            targets=targets,
        )

    def write_markdown_report(self, report: ImpactReport) -> Path:
        """
        Write a human-readable markdown impact report.

        Filename pattern:
            impact_report_<timestamp>.md
        Location:
            /reports/schema/
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"impact_report_{timestamp}.md"
        report_path = self.reports_dir / filename

        lines: List[str] = []
        lines.append("# Schema Impact Report\n")
        lines.append("")
        lines.append(f"- Diff Level: `{report.diff_level.name}`")
        lines.append(f"- Generated At (UTC): `{timestamp}`")
        lines.append(f"- Total Changes: `{len(report.changes)}`")
        lines.append(f"- Impacted Targets: `{len(report.targets)}`")
        lines.append("")
        lines.append("## Impacted Targets by Category")
        lines.append("")

        if not report.targets:
            lines.append("_No impacted targets detected._")
        else:
            grouped = report.targets_by_category()
            for category, targets in grouped.items():
                lines.append(f"### {category.value}")
                lines.append("")
                for idx, target in enumerate(targets, start=1):
                    rel_path = target.file_path.relative_to(self.project_root)
                    lines.append(f"#### {idx}. `{rel_path}`")
                    lines.append(f"- Category: `{category.value}`")
                    lines.append(f"- Reason: {target.reason}")
                    if target.related_changes:
                        lines.append(f"- Related Changes: `{len(target.related_changes)}`")
                        lines.append("")
                        lines.append("```text")
                        for ch in target.related_changes:
                            lines.append(
                                f"[{ch.change_type.name}/{ch.level.name}] "
                                f"{ch.path} -> {ch.message}"
                            )
                        lines.append("```")
                    lines.append("")
                lines.append("")

        report_content = "\n".join(lines)
        with report_path.open("w", encoding="utf-8") as f:
            f.write(report_content)

        logger.debug("Impact report written to %s", report_path)
        return report_path

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _group_changes_by_sheet(
        self,
        changes: Iterable[SchemaChange],
    ) -> Dict[str, List[SchemaChange]]:
        """
        Group changes by sheet name.
        Assumes SchemaChange.path starts with '<SheetName>.' or '<SheetName>'.
        """
        grouped: Dict[str, List[SchemaChange]] = {}
        for change in changes:
            sheet_name = self._extract_sheet_name_from_path(change.path)
            grouped.setdefault(sheet_name, []).append(change)
        logger.debug(
            "Grouped %d changes into %d sheet(s)",
            len(list(changes)),
            len(grouped),
        )
        return grouped

    @staticmethod
    def _extract_sheet_name_from_path(path: str) -> str:
        """
        Extract sheet name from change path.
        Examples:
            "Position.columns[Qty]" -> "Position"
            "DT_Report.row_start" -> "DT_Report"
            "Config" -> "Config"
        """
        if "." in path:
            return path.split(".", 1)[0]
        if "[" in path:
            return path.split("[", 1)[0]
        return path

    def _infer_targets_for_sheet(
        self,
        sheet_name: str,
        changes: List[SchemaChange],
    ) -> List[ImpactTarget]:
        """
        Infer impacted targets for a given sheet and its changes.

        This uses static mapping rules that can be adjusted as needed.
        """
        # Decide impact categories for this sheet
        categories = self._sheet_to_categories(sheet_name, changes)
        if not categories:
            logger.debug("No impact categories inferred for sheet '%s'", sheet_name)
            return []

        # Resolve file paths for each category
        targets: List[ImpactTarget] = []
        for category in categories:
            file_paths = self._category_to_files(sheet_name, category)
            for fp in file_paths:
                full_path = self.project_root / fp
                reason = self._build_reason(sheet_name, category, changes)
                target = ImpactTarget(
                    category=category,
                    file_path=full_path,
                    reason=reason,
                    related_changes=list(changes),
                )
                targets.append(target)
        return targets

    # -------------------------------------------------------------------------
    # Mapping rules
    # -------------------------------------------------------------------------

    def _sheet_to_categories(
        self,
        sheet_name: str,
        changes: List[SchemaChange],
    ) -> Set[ImpactCategory]:
        """
        Map sheet + change types to impact categories.

        Rules are based on ATS architecture:

        - Config          → ENGINE, RISK, STRATEGY
        - DT_Report       → REPOSITORY, ENGINE (trading, strategy), RISK
        - History         → REPOSITORY, RISK, DASHBOARD
        - Position        → REPOSITORY, ENGINE (portfolio), RISK, DASHBOARD
        - Strategy_Performance → REPOSITORY, STRATEGY, DASHBOARD
        - Other sheets    → SHEETS_ADAPTER or OTHER (depending on change type)
        """
        sheet_name_upper = sheet_name.upper()
        change_types = {ch.change_type for ch in changes}
        categories: Set[ImpactCategory] = set()

        # Config sheet
        if sheet_name_upper == "CONFIG":
            categories.update(
                {ImpactCategory.ENGINE, ImpactCategory.RISK, ImpactCategory.STRATEGY}
            )

        # Trade ledger
        elif sheet_name_upper in {"DT_REPORT", "T_LEDGER"}:
            categories.update(
                {
                    ImpactCategory.REPOSITORY,
                    ImpactCategory.ENGINE,
                    ImpactCategory.RISK,
                }
            )

        # Equity history
        elif sheet_name_upper == "HISTORY":
            categories.update(
                {
                    ImpactCategory.REPOSITORY,
                    ImpactCategory.RISK,
                    ImpactCategory.DASHBOARD,
                }
            )

        # Holdings / Position
        elif sheet_name_upper == "POSITION":
            categories.update(
                {
                    ImpactCategory.REPOSITORY,
                    ImpactCategory.ENGINE,
                    ImpactCategory.RISK,
                    ImpactCategory.DASHBOARD,
                }
            )

        # Strategy performance
        elif sheet_name_upper in {"STRATEGY_PERFORMANCE", "STRATEGY_STATS"}:
            categories.update(
                {
                    ImpactCategory.REPOSITORY,
                    ImpactCategory.STRATEGY,
                    ImpactCategory.DASHBOARD,
                }
            )

        # Risk dashboards
        elif sheet_name_upper in {"R_DASH", "RISK_MONITOR", "RISK_DASHBOARD"}:
            categories.update(
                {
                    ImpactCategory.RISK,
                    ImpactCategory.DASHBOARD,
                }
            )

        else:
            # Unknown / custom sheet: treat as sheets adapter & maybe dashboard
            categories.add(ImpactCategory.SHEETS_ADAPTER)
            # If blocks changed, probably dashboard-level impact too
            if any(ch.change_type == ChangeType.BLOCKS_CHANGED for ch in changes):
                categories.add(ImpactCategory.DASHBOARD)

        # If only metadata or column meta changed, we might downgrade to OTHER,
        # but here we keep original categories since they still matter for docs/UI.
        if change_types <= {ChangeType.SCHEMA_METADATA_CHANGED, ChangeType.COLUMN_META_CHANGED}:
            # The change is documentation-level; categorize as OTHER + maybe keep original.
            categories.add(ImpactCategory.OTHER)

        return categories

    def _category_to_files(
        self,
        sheet_name: str,
        category: ImpactCategory,
    ) -> List[Path]:
        """
        Map (sheet_name, category) into concrete file paths (relative to project_root).

        This mapping is heuristic and should be adjusted for the actual project.
        """
        # Base dirs according to Project_Folder_Convention
        src_root = Path("src")
        sheets_root = src_root / "sheets"
        engine_root = src_root / "engine"
        repo_root = src_root / "sheets"  # repositories often live under sheets/
        dashboard_root = src_root / "reporting"

        sheet_name_lower = sheet_name.lower()

        paths: List[Path] = []

        # Repository layer
        if category == ImpactCategory.REPOSITORY:
            if sheet_name_lower in {"dt_report", "t_ledger"}:
                paths.append(repo_root / "dt_report_repository.py")
            elif sheet_name_lower == "position":
                paths.append(repo_root / "position_repository.py")
            elif sheet_name_lower == "history":
                paths.append(repo_root / "history_repository.py")
            elif sheet_name_lower in {"strategy_performance", "strategy_stats"}:
                paths.append(repo_root / "strategy_performance_repository.py")
            else:
                paths.append(repo_root / f"{sheet_name_lower}_repository.py")

        # Engine layer
        if category == ImpactCategory.ENGINE:
            # Portfolio / trading engine
            if sheet_name_lower == "position":
                paths.append(engine_root / "portfolio" / "portfolio_engine.py")
            if sheet_name_lower in {"dt_report", "t_ledger"}:
                paths.append(engine_root / "trading" / "trading_engine.py")
            # Generic engine mapping
            paths.append(engine_root / "core" / "schema_dependent_engine.py")

        # Sheets adapter
        if category == ImpactCategory.SHEETS_ADAPTER:
            paths.append(sheets_root / "google_client.py")
            paths.append(sheets_root / f"{sheet_name_lower}_adapter.py")

        # Risk
        if category == ImpactCategory.RISK:
            paths.append(engine_root / "risk" / "risk_engine.py")
            paths.append(engine_root / "risk" / "portfolio_risk.py")

        # Strategy
        if category == ImpactCategory.STRATEGY:
            paths.append(engine_root / "strategy" / "strategy_engine.py")

        # Dashboard / reporting
        if category == ImpactCategory.DASHBOARD:
            paths.append(dashboard_root / "portfolio_dashboard_renderer.py")
            paths.append(dashboard_root / "risk_dashboard_renderer.py")

        # Other
        if category == ImpactCategory.OTHER:
            paths.append(src_root / "core" / "schema_aware_context.py")

        # Deduplicate
        unique_paths: List[Path] = []
        seen: Set[Path] = set()
        for p in paths:
            if p not in seen:
                seen.add(p)
                unique_paths.append(p)

        return unique_paths

    @staticmethod
    def _build_reason(
        sheet_name: str,
        category: ImpactCategory,
        changes: List[SchemaChange],
    ) -> str:
        """
        Build a concise human-readable reason string for the target.
        """
        change_types: Set[ChangeType] = {ch.change_type for ch in changes}
        level = ChangeLevel.max_level([ch.level for ch in changes])
        change_type_names = ", ".join(sorted(ct.name for ct in change_types))

        return (
            f"Sheet '{sheet_name}' changed (types: {change_type_names}) "
            f"with overall level {level.name}, which affects '{category.value}' layer."
        )
