import os
import shutil

OLD_NAME = "auto_trading_system.schemas.json"
NEW_NAME = "auto_trading_system.schemas.json"

SEARCH_DIRS = ["src", "config", "tools", "tests"]  # 원하는 폴더 확장 가능
BACKUP_SUFFIX = ".bak_schema_rename"

def rename_schema_file(project_root):
    old_path = os.path.join(project_root, "config", OLD_NAME)
    new_path = os.path.join(project_root, "config", NEW_NAME)

    if os.path.exists(old_path):
        print(f"[RENAME] Renaming schemas file:\n  {old_path} → {new_path}")
        os.rename(old_path, new_path)
    else:
        print(f"[SKIP] Schema file not found: {old_path}")


def replace_in_file(filepath):
    """파일 내부에서 OLD_NAME → NEW_NAME 문자열 치환"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = f.read()

        if OLD_NAME not in data:
            return False  # 수정 없음

        backup_path = filepath + BACKUP_SUFFIX
        shutil.copyfile(filepath, backup_path)

        new_data = data.replace(OLD_NAME, NEW_NAME)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_data)

        print(f"[UPDATED] {filepath}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to update {filepath}: {e}")
        return False


def scan_and_replace(project_root):
    modified_files = []

    for search_dir in SEARCH_DIRS:
        full_dir = os.path.join(project_root, search_dir)

        if not os.path.exists(full_dir):
            continue

        for root, _, files in os.walk(full_dir):
            for file in files:
                if not file.endswith((".py", ".json", ".md", ".yaml")):
                    continue  # 스키마 참조 가능성이 있는 파일만 검사

                filepath = os.path.join(root, file)
                if replace_in_file(filepath):
                    modified_files.append(filepath)

    print("\n=== Summary ===")
    print(f"Modified {len(modified_files)} files.")
    for f in modified_files:
        print(f" - {f}")


def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print(f"[Project Root] {project_root}")

    rename_schema_file(project_root)
    scan_and_replace(project_root)


if __name__ == "__main__":
    main()
