# src/brokers/test_broker.py

import os
import sys
from dotenv import load_dotenv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]  # 프로젝트 루트
load_dotenv(ROOT / ".env")

# src 폴더를 import path에 추가 (모듈 실행 오류 방지)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
sys.path.append(SRC_DIR)

from brokers.kis_broker import KISBroker


def test_broker():
    print("=== 1) Broker 초기화 ===")
    broker = KISBroker()

    print("\n=== 2) Token 테스트 ===")
    token = broker.get_token()
    print("TOKEN:", token[:10], "...")

    print("\n=== 3) 국내 현재가 조회 ===")
    price = broker.get_price("005930")
    print("PRICE(005930):", price)

    print("\n=== 4) 잔고 조회 ===")
    bal = broker.get_balance()
    print("BALANCE:", bal)

    print("\n=== 5) 보유 종목 조회 ===")
    pos = broker.get_positions()
    print("POSITIONS:", pos)

    print("\n=== 6) 매수 테스트 ===")
    buy = broker.buy("005930", qty=1)
    print("BUY RESULT:", buy)

    print("\n=== 7) 매도 테스트 ===")
    sell = broker.sell("005930", qty=1)
    print("SELL RESULT:", sell)


# ===================== 중요 =====================
# 모듈 실행 시 test_broker() 실행
# =====================
if __name__ == "__main__":
    test_broker()
