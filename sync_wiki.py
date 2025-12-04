import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# ==== 사용자 설정 ====
REPO = "tawbury/Auto_Trading_System"
BRANCH = "main"

def run(cmd, cwd=None):
    print(f"[RUN] {cmd}")
    subprocess.run(cmd, cwd=cwd, shell=True, check=True)

def clone_wiki(tmp_dir: Path) -> Path:
    wiki_url = f"https://github.com/{REPO}.wiki.git"
    wiki_path = tmp_dir / "Auto_Trading_System.wiki"

    print("\n=== Clone Wiki Repository ===")
    run(f"git clone {wiki_url}", cwd=tmp_dir)

    # 폴더 이름 자동 감지 (git이 폴더명을 repo명.wiki로 생성)
    if wiki_path.exists():
        return wiki_path
    else:
        # 폴더명을 동적으로 탐색
        for child in tmp_dir.iterdir():
            if child.is_dir() and child.name.endswith(".wiki"):
                return child

    raise Exception("Wiki repo clone 실패: *.wiki 폴더를 찾을 수 없음")

def sync_docs_to_wiki(wiki_path: Path):
    docs_wiki_path = Path("./docs/wiki")

    if not docs_wiki_path.exists():
        raise Exception("docs/wiki 폴더가 존재하지 않습니다.")

    print("\n=== Sync docs/wiki/*.md → wiki repo ===")

    # wiki 폴더가 비어있거나 구조가 없다면 생성
    wiki_path.mkdir(parents=True, exist_ok=True)

    for md_file in docs_wiki_path.glob("*.md"):
        dest = wiki_path / md_file.name

        # 대상 파일 폴더 생성
        dest.parent.mkdir(parents=True, exist_ok=True)

        print(f"[COPY] {md_file} → {dest}")
        shutil.copy(md_file, dest)

def main():
    print("=========================================")
    print(" Auto Trading System - Wiki Sync Tool")
    print(" docs/wiki → GitHub Wiki")
    print("=========================================\n")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        wiki_path = clone_wiki(tmp_dir)
        sync_docs_to_wiki(wiki_path)

        print("\n=== Commit & Push to GitHub Wiki ===")
        try:
            run("git add .", cwd=wiki_path)
            run('git commit -m "Update Wiki from docs/wiki folder"', cwd=wiki_path)
            run("git push", cwd=wiki_path)
            print("\n=== 완료: GitHub Wiki 업데이트 성공! ===")
        except subprocess.CalledProcessError:
            print("\n=== 변경사항 없음 → commit 생략됨 ===")

if __name__ == "__main__":
    main()
