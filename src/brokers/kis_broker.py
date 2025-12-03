# src/brokers/kis_broker.py
import os
import time
import requests
from dotenv import load_dotenv

from .broker_interface import BrokerInterface

load_dotenv()


class KISBroker(BrokerInterface):

    def __init__(self):
        self.app_key = os.getenv("APP_KEY")
        self.app_secret = os.getenv("APP_SECRET")
        self.account_no = os.getenv("ACCOUNT_NO")
        self.acnt_prdt_cd = os.getenv("ACNT_PRDT_CD", "01")

        # 모의투자용 Base URL
        self.base_url = os.getenv("URL_BASE", "https://openapivts.koreainvestment.com:29443")

        # 모의투자 Token URL
        self.TOKEN_URL = "https://openapivts.koreainvestment.com:29443/oauth2/token"

        self.access_token = None
        self.token_expiry = 0

    # =========================================================
    # Token 발급 + 캐싱(10초 내 재발급 금지)
    # =========================================================
    def get_token(self):
        # 이미 토큰이 있고 유효시간 남아있으면 재사용
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        # 새 토큰 발급
        headers = {"Content-Type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        res = requests.post(self.TOKEN_URL, headers=headers, json=body)
        res.raise_for_status()

        data = res.json()
        self.access_token = data["access_token"]

        # 토큰 만료시간(유효기간 1시간) 설정
        self.token_expiry = time.time() + 3500

        return self.access_token

    # =========================================================
    # 공통 헤더 생성
    # =========================================================
    def _build_headers(self, tr_id=""):
        token = self.get_token()
        return {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    # =========================================================
    # 국내 현재가 조회
    # =========================================================
    def get_price(self, symbol: str) -> float:
        headers = self._build_headers(tr_id="FHKST01010100")

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol
        }

        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()

        data = r.json()
        return float(data["output"]["stck_prpr"])

    # =========================================================
    # 해외 현재가 조회
    # =========================================================
    def get_overseas_price(self, exch: str, symbol: str) -> float:
        headers = self._build_headers(tr_id="HHDFS00000300")

        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"
        params = {
            "AUTH": "",
            "EXCD": exch,
            "SYMB": symbol
        }

        r = requests.get(url, headers=headers, params=params)
        data = r.json()

        # 정상 응답 처리
        if "output" in data and "last" in data["output"]:
            try:
                return float(data["output"]["last"])
            except:
                pass

        # 오류가 발생한 경우 → 세분화된 메세지 출력
        err_cd = data.get("msg_cd", "")
        err_msg = data.get("msg1", "")

        print(f"[해외 시세 조회 오류] {symbol} / {exch}")
        print(f"코드={err_cd} / 메세지={err_msg}")
        print("전체응답:", data)

        return 0.0

    # =========================================================
    # 아래 기능들은 추후 구현
    # =========================================================
    def buy(self, symbol: str, qty: int, **kwargs):
        return {"status": "NOT_IMPLEMENTED"}

    def sell(self, symbol: str, qty: int, **kwargs):
        return {"status": "NOT_IMPLEMENTED"}

    def get_positions(self):
        return []

    def get_balance(self):
        return {}
