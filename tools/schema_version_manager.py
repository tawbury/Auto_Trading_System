import os
import json
import re
from typing import Dict, Tuple, List, Optional, Set

# ===============================================================
# 설정 영역
# ===============================================================

# 스키마 파일명 (프로젝트 내 통일된 이름)
SCHEMA_FILENAME = "auto_trading_system.schemas.json"

# 스키마 및 히스토리 디렉토리
CONFIG_DIR = "config"
HISTORY_DIR_NAME = "schema_history"

# 히스토리 파일명 패턴: auto_trading_system.schemas.vX.Y.Z.json
HISTORY_PREFIX = "auto_trading_system.schemas.v"
HISTORY_SUFFIX = ".json"

# Summary markdown 출력 디렉토리 및 파일명
REPORT_DIR = "reports/schemas"
REPORT_PATH = os.path.join(REPORT_DIR, "schema_output.md")

# 시트별로 영향을 받는 Repository 파일 매핑
# 필요 시 자유롭게 확장 가능
SHEET_REPO_MAP: Dict[str, List[str]] = {
    "Config": [
        "src/sheets/config_repository.py",
        "src/core/app_context.py",
    ],
    "DT_Report": [
        "src/sheets/dt_report_repository.py",
        "src/engine/trading/trading_engine.py",
    ],
    "Position": [
        "src/sheets/position_repository.py",
    ],
    "History": [
        "src/sheets/history_repository.py",
    ],
    "DI_DB": [
        "src/sheets/di_db_repository.py",
    ],
    "Strategy_Performance": [
        "src/sheets/strategy_performance_repository.py",
    ],
    # 필요하면 향후 Portfolio_Dashboard, Risk_Dashboard 등도 추가 가능
}


# ===============================================================
# 기본 유틸 함수
# ===============================================================

def get_project_root() -> str:
    """
    현재 파일(tools/schema_version_manager.py)을 기준으로
    프로젝트 루트 경로를 계산.
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_json(path: str) -> Dict:
    """JSON 파일 로드"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict) -> None:
    """JSON 파일 저장 (상위 디렉토리가 없으면 자동 생성)"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_version(ver: str) -> Tuple[int, int, int]:
    """'3.5.0' → (3, 5, 0) 형태로 변환"""
    parts = ver.split(".")
    return tuple(int(x) for x in parts)


def bump_version(old_ver: str, level: str) -> str:
    """
    변경 레벨(MAJOR/MINOR/PATCH)에 따라 버전 증가
      - MAJOR: (x+1).0.0
      - MINOR: x.(y+1).0
      - PATCH: x.y.(z+1)
    """
    major, minor, patch = parse_version(old_ver)

    if level == "MAJOR":
        major += 1
        minor = 0
        patch = 0
    elif level == "MINOR":
        minor += 1
        patch = 0
    elif level == "PATCH":
        patch += 1

    return f"{major}.{minor}.{patch}"


# ===============================================================
# 히스토리 파일 관리
# ===============================================================

def find_latest_history_file(history_dir: str) -> Optional[Tuple[str, str]]:
    """
    schema_history 디렉토리 내에서
    auto_trading_system.schemas.vX.Y.Z.json 파일 중
    가장 최근 버전을 찾아 (version_str, path) 를 반환.
    """
    if not os.path.exists(history_dir):
        return None

    pattern = re.compile(rf"^{re.escape(HISTORY_PREFIX)}(\d+\.\d+\.\d+){re.escape(HISTORY_SUFFIX)}$")
    candidates: List[Tuple[Tuple[int, int, int], str, str]] = []

    for fname in os.listdir(history_dir):
        m = pattern.match(fname)
        if not m:
            continue
        ver_str = m.group(1)
        ver_tuple = parse_version(ver_str)
        full_path = os.path.join(history_dir, fname)
        candidates.append((ver_tuple, ver_str, full_path))

    if not candidates:
        return None

    # 버전(major, minor, patch)을 기준으로 정렬 후 가장 큰 버전 선택
    candidates.sort(key=lambda x: x[0])
    _, ver_str, path = candidates[-1]
    return ver_str, path


# ===============================================================
# 스키마 구조 비교 (Diff + Impact)
# ===============================================================

def compare_schemas(old: Dict, new: Dict) -> Tuple[str, List[str], Set[str]]:
    """
    old vs new 스키마 구조 비교.
    반환:
      - change_level: "NO_CHANGE" | "PATCH" | "MINOR" | "MAJOR"
      - changes: 변경 사항을 설명하는 텍스트 리스트
      - affected_sheets: 구조 변경이 발생한 시트명 집합
    """
    changes: List[str] = []
    change_level = "NO_CHANGE"
    affected_sheets: Set[str] = set()

    def escalate(level: str):
        """변경 레벨 우선순위에 따라 change_level 갱신"""
        nonlocal change_level
        priority = {"NO_CHANGE": 0, "PATCH": 1, "MINOR": 2, "MAJOR": 3}
        if priority[level] > priority[change_level]:
            change_level = level

    old_sheets = old.get("sheets", {})
    new_sheets = new.get("sheets", {})

    old_sheet_names = set(old_sheets.keys())
    new_sheet_names = set(new_sheets.keys())

    # 1) 시트 추가
    for sheet in sorted(new_sheet_names - old_sheet_names):
        changes.append(f"+ Added sheet: {sheet}")
        escalate("MINOR")
        affected_sheets.add(sheet)

    # 2) 시트 삭제
    for sheet in sorted(old_sheet_names - new_sheet_names):
        changes.append(f"- Removed sheet: {sheet}")
        escalate("MAJOR")
        affected_sheets.add(sheet)

    # 3) 공통 시트 내부 구조 비교
    for sheet in sorted(old_sheet_names & new_sheet_names):
        old_def = old_sheets.get(sheet, {})
        new_def = new_sheets.get(sheet, {})

        # row_start 변경 체크
        old_row = old_def.get("row_start")
        new_row = new_def.get("row_start")
        if old_row != new_row:
            changes.append(f"* Sheet '{sheet}': row_start {old_row} → {new_row}")
            escalate("MAJOR")
            affected_sheets.add(sheet)

        old_cols = old_def.get("columns", {})
        new_cols = new_def.get("columns", {})

        old_cols_keys = set(old_cols.keys())
        new_cols_keys = set(new_cols.keys())

        # 컬럼 추가
        for col in sorted(new_cols_keys - old_cols_keys):
            changes.append(f"+ Sheet '{sheet}': added column '{col}' ({new_cols[col]})")
            escalate("MINOR")
            affected_sheets.add(sheet)

        # 컬럼 삭제
        for col in sorted(old_cols_keys - new_cols_keys):
            changes.append(f"- Sheet '{sheet}': removed column '{col}'")
            escalate("MAJOR")
            affected_sheets.add(sheet)

        # 컬럼 위치 변경
        for col in sorted(old_cols_keys & new_cols_keys):
            if old_cols[col] != new_cols[col]:
                changes.append(
                    f"* Sheet '{sheet}': column '{col}' {old_cols[col]} → {new_cols[col]}"
                )
                escalate("MAJOR")
                affected_sheets.add(sheet)

    return change_level, changes, affected_sheets


# ===============================================================
# Markdown Summary 생성 (Summary + Changes + Impact)
# ===============================================================

def write_markdown_report(
    level: str,
    old_ver: str,
    new_ver: str,
    changes: List[str],
    history_path: str,
    impact_map: Dict[str, List[str]],
) -> None:
    """
    GitHub PR 코멘트용 스키마 변경 요약 마크다운 생성.
    출력 위치: /reports/schemas/schema_output.md
    """
    os.makedirs(REPORT_DIR, exist_ok=True)

    lines: List[str] = []
    lines.append("## Schema Update Summary\n")
    lines.append(f"**Change Level:** {level}")
    lines.append(f"**Old Version:** {old_ver}")
    lines.append(f"**New Version:** {new_ver}\n")

    # 변경 내역
    lines.append("### Changes:")
    if changes:
        for ch in changes:
            lines.append(f"- {ch}")
    else:
        lines.append("*No structural changes detected.*")

    # Impact Analysis 섹션
    lines.append("\n### Impact Analysis:")
    if impact_map:
        for sheet, repos in impact_map.items():
            lines.append(f"- Sheet `{sheet}` may affect:")
            for repo in repos:
                lines.append(f"  - `{repo}`")
    else:
        lines.append("*No impacted repositories detected (or no mapping configured).*")

    # 히스토리 파일 경로
    lines.append("\n### History Snapshot:")
    lines.append(f"`{history_path}`\n")

    # 파일 쓰기
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[Markdown] Summary & Impact report created at {REPORT_PATH}")


# ===============================================================
# 메인 로직
# ===============================================================

def main():
    project_root = get_project_root()
    config_dir = os.path.join(project_root, CONFIG_DIR)
    history_dir = os.path.join(config_dir, HISTORY_DIR_NAME)
    schema_path = os.path.join(config_dir, SCHEMA_FILENAME)

    print(f"[Schema] Current Schema File: {schema_path}")

    current = load_json(schema_path)
    latest = find_latest_history_file(history_dir)

    # 1) 히스토리가 전혀 없을 때: 초기 baseline 생성
    if latest is None:
        base_ver = current.get("schema_version", "1.0.0")
        baseline_path = os.path.join(history_dir, f"{HISTORY_PREFIX}{base_ver}{HISTORY_SUFFIX}")
        save_json(baseline_path, current)

        # 초기 상태에서는 영향받는 시트/레포지토리가 없으므로 빈 맵 전달
        write_markdown_report("NO_CHANGE", base_ver, base_ver, [], baseline_path, {})
        print("[Init] Baseline schemas history created.")
        return

    # 2) 기존 히스토리가 있는 경우 → 최신 버전과 비교
    old_ver_str, old_path = latest
    old_schema = load_json(old_path)

    # 구조 비교 + 영향 시트 수집
    level, changes, affected_sheets = compare_schemas(old_schema, current)
    print(f"[Diff] Change Level: {level}")
    print(f"[Diff] Affected Sheets: {', '.join(sorted(affected_sheets)) if affected_sheets else 'None'}")

    # 버전 증가
    new_ver_str = bump_version(old_ver_str, level)
    current["schema_version"] = new_ver_str
    save_json(schema_path, current)

    # 새 히스토리 생성
    new_history_path = os.path.join(
        history_dir,
        f"{HISTORY_PREFIX}{new_ver_str}{HISTORY_SUFFIX}"
    )
    save_json(new_history_path, current)

    # 3) Impact Analysis: 시트 → Repository 매핑
    impact_map: Dict[str, List[str]] = {}
    for sheet in sorted(affected_sheets):
        repos = SHEET_REPO_MAP.get(sheet)
        if repos:
            impact_map[sheet] = repos

    # Markdown 리포트 작성
    write_markdown_report(level, old_ver_str, new_ver_str, changes, new_history_path, impact_map)

    print(f"[Done] Schema version updated to {new_ver_str}")
    print(f"[Done] Markdown summary with impact analysis stored at {REPORT_PATH}")


if __name__ == "__main__":
    main()
