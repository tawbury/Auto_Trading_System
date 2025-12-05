"""
SchemaVersionManager
---------------------
스키마 파일 버전 관리, 최신 버전 로딩, 새 버전 저장 기능 제공.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from tools.schema.schema_diff import SchemaDiffResult, ChangeLevel


class SchemaVersionManager:

    def __init__(self, project_root: Path):
        self.schemas_dir = project_root / "schemas"
        self.history_dir = self.schemas_dir / "history"

        self.schemas_dir.mkdir(exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

        self.master_schema_path = self.schemas_dir / "auto_trading_system.schema.json"

    # ---------------------------------------------------------
    # Load latest schema
    # ---------------------------------------------------------
    def load_latest_schema(self) -> Optional[Dict[str, Any]]:
        """
        기존 최신 스키마 파일을 로딩한다.
        없으면 None 반환.
        """
        if not self.master_schema_path.exists():
            return None
        return json.loads(self.master_schema_path.read_text(encoding="utf-8"))

    # ---------------------------------------------------------
    # Save new schema with version bump
    # ---------------------------------------------------------
    def update_version(self, new_schema: Dict[str, Any], diff: SchemaDiffResult) -> Path:
        """
        diff 정보에 따라 version bump 후 저장.
        이전 버전은 history에 백업.
        """
        old_schema = self.load_latest_schema()

        if old_schema:
            old_version = old_schema.get("schema_version", "0.0")
        else:
            old_version = "0.0"

        new_version = self._bump_version(old_version, diff.level)
        new_schema["schema_version"] = new_version

        # 1) Backup old schema if exists
        if old_schema:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.history_dir / f"schema_{timestamp}.json"
            backup_path.write_text(json.dumps(old_schema, indent=2, ensure_ascii=False), encoding="utf-8")

        # 2) Save new master schema
        self.master_schema_path.write_text(
            json.dumps(new_schema, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return self.master_schema_path

    # ---------------------------------------------------------
    # Version bump logic
    # ---------------------------------------------------------
    @staticmethod
    def _bump_version(version: str, level: ChangeLevel) -> str:
        """
        SemVer version string을 유연하게 파싱:
        1) X.Y.Z
        2) X.Y
        모두 지원하도록 정규화.
        """

        parts = version.split(".")
        parts = [int(p) for p in parts]

        # 길이에 따라 보정
        if len(parts) == 1:  # e.g., "3"
            major, minor, patch = parts[0], 0, 0
        elif len(parts) == 2:  # e.g., "3.6"
            major, minor = parts
            patch = 0
        elif len(parts) >= 3:  # e.g., "3.6.1"
            major, minor, patch = parts[:3]
        else:
            major, minor, patch = 0, 0, 0

        # bump logic
        if level == ChangeLevel.MAJOR:
            major += 1
            minor = 0
            patch = 0
        elif level == ChangeLevel.MINOR:
            minor += 1
            patch = 0
        elif level == ChangeLevel.PATCH:
            patch += 1

        return f"{major}.{minor}.{patch}"
