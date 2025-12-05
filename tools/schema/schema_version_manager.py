"""
schema_version_manager.py

Schema Version Manager for ATS Schema Engine.

Responsibilities:
- Interpret SchemaDiffResult to decide new semantic version (major/minor/patch).
- Persist new versioned schema into /schemas and /schemas/history.
- Generate human-readable diff summary reports under /reports/schema.

This module is filesystem-aware but still focused on versioning concerns only.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from .diff_engine_v2 import (
    ChangeLevel,
    SchemaDiffResult,
    SchemaChange,
)

logger = logging.getLogger(__name__)


class SemanticVersionError(Exception):
    """Raised when a semantic version string is invalid."""
    pass


@dataclass(frozen=True)
class SemanticVersion:
    """Simple semantic version representation: major.minor.patch."""
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version_str: str) -> "SemanticVersion":
        try:
            parts = version_str.strip().split(".")
            if len(parts) != 3:
                raise ValueError("Expected three components 'major.minor.patch'")
            major, minor, patch = (int(p) for p in parts)
            return cls(major=major, minor=minor, patch=patch)
        except Exception as exc:  # noqa: BLE001
            raise SemanticVersionError(f"Invalid semantic version string: {version_str!r}") from exc

    def bump(self, level: ChangeLevel) -> "SemanticVersion":
        if level == ChangeLevel.PATCH:
            return SemanticVersion(self.major, self.minor, self.patch + 1)
        if level == ChangeLevel.MINOR:
            return SemanticVersion(self.major, self.minor + 1, 0)
        if level in (ChangeLevel.MAJOR, ChangeLevel.BREAKING):
            # BREAKING도 MAJOR로 취급, 필요 시 별도 정책으로 분리 가능
            return SemanticVersion(self.major + 1, 0, 0)
        # Fallback
        return self

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class VersionDecision(Enum):
    """How to treat the diff when deciding version."""
    NO_CHANGE = "no_change"
    BUMP = "bump"


@dataclass
class VersioningResult:
    """Result of applying versioning logic to a schema."""
    decision: VersionDecision
    old_version: Optional[str]
    new_version: Optional[str]
    diff_level: ChangeLevel
    schema_path: Optional[Path] = None
    history_path: Optional[Path] = None
    report_path: Optional[Path] = None


class SchemaVersionManager:
    """
    SchemaVersionManager encapsulates all logic to:
    - Decide new version from SchemaDiffResult
    - Persist updated schema JSON to /schemas + /schemas/history
    - Emit markdown diff summary to /reports/schema

    It does NOT run the diff itself; that is the responsibility of SchemaDiffEngine.
    """

    def __init__(
        self,
        project_root: Path,
        schema_filename: str = "auto_trading_system.schema.json",
        reports_dir: str = "reports/schema",
        history_dir: str = "schemas/history",
    ) -> None:
        self.project_root = project_root
        self.schema_path = project_root / "schemas" / schema_filename
        self.history_dir = project_root / history_dir
        self.reports_dir = project_root / reports_dir

        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(
            "SchemaVersionManager initialized with project_root=%s, schema_path=%s",
            self.project_root,
            self.schema_path,
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def apply_versioning(
        self,
        current_schema: Dict[str, Any],
        diff_result: SchemaDiffResult,
        current_version_str: Optional[str] = None,
    ) -> VersioningResult:
        """
        Apply versioning based on diff result and current version.

        :param current_schema: The new validated schema dict to be saved.
        :param diff_result: Result from SchemaDiffEngine.
        :param current_version_str: Current semantic version string (e.g. "3.1.0").
                                    If None, it will try to read from schema["version"].
        """
        logger.info("Applying schema versioning, diff level=%s", diff_result.level.name)

        if diff_result.is_empty():
            logger.info("No schema changes detected. Version will not be bumped.")
            return VersioningResult(
                decision=VersionDecision.NO_CHANGE,
                old_version=current_version_str,
                new_version=current_version_str,
                diff_level=ChangeLevel.PATCH,
            )

        # 1) Determine old version
        old_version_str = self._resolve_current_version(current_schema, current_version_str)
        old_semver = SemanticVersion.parse(old_version_str)

        # 2) Decide new version
        new_semver = old_semver.bump(diff_result.level)
        new_version_str = str(new_semver)

        # 3) Attach new version to schema dict
        current_schema_with_version = dict(current_schema)
        current_schema_with_version["version"] = new_version_str

        # 4) Persist schema JSON to main path and history path
        history_path = self._write_schema_history_file(
            current_schema_with_version,
            new_version_str,
        )
        schema_path = self._write_current_schema_file(current_schema_with_version)

        # 5) Write diff summary report (markdown)
        report_path = self._write_diff_summary_report(
            diff_result=diff_result,
            old_version=old_version_str,
            new_version=new_version_str,
        )

        logger.info(
            "Schema versioning done: %s -> %s (level=%s)",
            old_version_str,
            new_version_str,
            diff_result.level.name,
        )

        return VersioningResult(
            decision=VersionDecision.BUMP,
            old_version=old_version_str,
            new_version=new_version_str,
            diff_level=diff_result.level,
            schema_path=schema_path,
            history_path=history_path,
            report_path=report_path,
        )

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _resolve_current_version(
        self,
        schema: Dict[str, Any],
        explicit_version: Optional[str],
    ) -> str:
        """
        Decide the current version string from explicit arg or schema["version"].

        If neither is provided, default to "0.0.0" (unversioned initial schema).
        """
        if explicit_version:
            logger.debug("Using explicit current_version=%s", explicit_version)
            return explicit_version

        schema_version = schema.get("version")
        if isinstance(schema_version, str):
            logger.debug("Using schema['version']=%s as current version", schema_version)
            return schema_version

        logger.warning(
            "No explicit current version and schema['version'] missing. "
            "Falling back to '0.0.0' as initial version."
        )
        return "0.0.0"

    def _write_current_schema_file(
        self,
        schema: Dict[str, Any],
    ) -> Path:
        """
        Write the latest schema JSON to the canonical schema path.

        :return: Path to the written file.
        """
        self.schema_path.parent.mkdir(parents=True, exist_ok=True)
        with self.schema_path.open("w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
        logger.debug("Current schema written to %s", self.schema_path)
        return self.schema_path

    def _write_schema_history_file(
        self,
        schema: Dict[str, Any],
        version_str: str,
    ) -> Path:
        """
        Save the schema into a versioned history file.

        Filename pattern:
            <timestamp>_v<version>.schema.json
        Example:
            2025-12-05T21-30-01_v3.1.1.schema.json
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"{timestamp}_v{version_str}.schema.json"
        history_path = self.history_dir / filename

        with history_path.open("w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)

        logger.debug("Schema history written to %s", history_path)
        return history_path

    def _write_diff_summary_report(
        self,
        diff_result: SchemaDiffResult,
        old_version: str,
        new_version: str,
    ) -> Path:
        """
        Write a human-readable diff summary markdown file.

        File path pattern:
            reports/schema/diff_summary_<timestamp>.md

        Additionally, you may decide to keep only the latest or append to a single file.
        Here we create a timestamped file for clarity.
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        filename = f"diff_summary_{timestamp}.md"
        report_path = self.reports_dir / filename

        lines = []
        lines.append("# Schema Diff Summary\n")
        lines.append("")
        lines.append(f"- Old Version: `{old_version}`")
        lines.append(f"- New Version: `{new_version}`")
        lines.append(f"- Diff Level: `{diff_result.level.name}`")
        lines.append(f"- Generated At (UTC): `{timestamp}`")
        lines.append("")
        lines.append("## Changes")
        lines.append("")

        if not diff_result.changes:
            lines.append("_No changes detected._")
        else:
            for idx, change in enumerate(diff_result.changes, start=1):
                lines.extend(self._format_change_markdown(idx, change))

        report_content = "\n".join(lines)
        with report_path.open("w", encoding="utf-8") as f:
            f.write(report_content)

        logger.debug("Diff summary report written to %s", report_path)
        return report_path

    # -------------------------------------------------------------------------
    # Markdown formatting
    # -------------------------------------------------------------------------

    def _format_change_markdown(self, index: int, change: SchemaChange) -> list[str]:
        """
        Format a single SchemaChange as markdown bullet section.
        """
        lines: list[str] = []
        lines.append(f"### {index}. `{change.change_type.name}` ({change.level.name})")
        lines.append("")
        lines.append(f"- **Path**: `{change.path}`")
        lines.append(f"- **Message**: {change.message}")
        if change.old_value is not None:
            lines.append(f"- **Old**: `{self._safe_repr(change.old_value)}`")
        if change.new_value is not None:
            lines.append(f"- **New**: `{self._safe_repr(change.new_value)}`")
        lines.append("")
        return lines

    @staticmethod
    def _safe_repr(value: Any, max_len: int = 200) -> str:
        """
        Safe and concise repr for values in markdown report.
        """
        try:
            text = repr(value)
        except Exception:  # noqa: BLE001
            text = "<unrepr-able>"
        if len(text) > max_len:
            text = text[: max_len - 3] + "..."
        return text
