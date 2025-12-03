# main.py
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
root = Path(__file__).resolve().parent

# src 폴더를 Python 경로에 등록
sys.path.append(str(root / "src"))

from core.app_context import AppContext


def main():
    print("### Auto Trading System Start ###")

    # AppContext 초기화 (Google Sheets / Schema / Broker / Engine 로드)
    ctx = AppContext(root)

    print("\n### 포트폴리오 상태 ###")
    state = ctx.portfolio.build_portfolio_state()
    print(state)


if __name__ == "__main__":
    main()
