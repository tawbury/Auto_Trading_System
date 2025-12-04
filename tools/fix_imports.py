import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # Auto_Trading_System 폴더
SRC = ROOT / "src"

# 잘못된 패턴: from src.xxx import Y
pattern = re.compile(r"from\s+src\.([a-zA-Z0-9_\.]+)\s+import\s+(.*)")

# 잘못된 패턴: import src.xxx
pattern2 = re.compile(r"import\s+src\.([a-zA-Z0-9_\.]+)")

def fix_line(line: str):
    # 패턴1: from src.xxx import Y
    m = pattern.search(line)
    if m:
        module = m.group(1)
        imports = m.group(2)
        return f"from {module} import {imports}\n"

    # 패턴2: import src.xxx
    m2 = pattern2.search(line)
    if m2:
        module = m2.group(1)
        return f"import {module}\n"

    return line


def run():
    print(f"[FixImports] Scanning: {SRC}")

    py_files = list(SRC.rglob("*.py"))

    fixed_files = 0

    for file in py_files:
        original = file.read_text(encoding="utf-8")
        lines = original.splitlines(keepends=True)

        modified = False
        new_lines = []

        for line in lines:
            new_line = fix_line(line)
            if new_line != line:
                modified = True
            new_lines.append(new_line)

        if modified:
            file.write_text("".join(new_lines), encoding="utf-8")
            print(f"[FixImports] Fixed: {file}")
            fixed_files += 1

    print(f"[FixImports] Completed. Modified files: {fixed_files}")


if __name__ == "__main__":
    run()
