# src/brokers/kis_broker.py
# 한국투자증권 OpenAPI(REST) 브로커 구현
# REAL/VTS 완전 분리, Token 캐싱, Content-Type 정책, 잔고/보유종목 구조 자동 보정

import os
import time
import json
import threading
import requests
import pathlib
from dotenv import load_dotenv

from brokers.broker_interface import BrokerInterface  # 경로 고정

# ===============================================================
# 1) 프로젝트 루트에서 .env 강제 로드
# ===============================================================
ROOT = pathlib.Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
load_dotenv(ENV_PATH)

# ===============================================================
# 2) Token 캐시 파일 정의
# ===============================================================
TOKEN_CACHE_FILE = ROOT / "cache/kis_token.json"
token_lock = threading.Lock()


def get_cached_token():
    """캐시 파일에서 토큰 로드"""
    if TOKEN_CACHE_FILE.exists():
        try:
            with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    return None


def save_cached_token(token_data):
    """토큰 캐시 저장"""
    TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f)


# ===============================================================
# 3) KISBroker 본체
# ===============================================================
class KISBroker(BrokerInterface):

    def __init__(self):
        """
        한국투자증권 REST 브로커 초기화
        - REAL/VTS 완전 분리
        - BASE_URL 분리
        - 실전주문 보호
        """
        # 운영모드: REAL / VTS
        self.mode = os.getenv("KIS_MODE", "VTS").upper()
        self.enable_real_order = os.getenv("ENABLE_REAL_ORDER", "N").upper() == "Y"

        # REAL_ / VTS_ prefix
        prefix = "REAL_" if self.mode == "REAL" else "VTS_"

        self.app_key = os.getenv(f"{prefix}APP_KEY")
        self.app_secret = os.getenv(f"{prefix}APP_SECRET")
        self.account_no = os.getenv(f"{prefix}ACCOUNT_NO")
        self.acnt_prdt_cd = os.getenv(f"{prefix}ACNT_PRDT_CD", "01")

        # BASE_URL 분리
        vts_url = os.getenv("VTS_BASE_URL", "").strip()
        real_url = os.getenv("REAL_BASE_URL", "").strip()

        if self.mode == "REAL":
            self.base_url = real_url
            self.TOKEN_URL = f"{real_url}/oauth2/tokenP"
        else:
            self.base_url = vts_url
            self.TOKEN_URL = f"{vts_url}/oauth2/tokenP"

        # 메모리 캐시
        self.access_token = None
        self.token_expiry = 0

        # === 디버그 출력 ===
        print("\n[DEBUG ENV CHECK]")
        print("MODE =", self.mode)
        print("app_key =", self.app_key)
        print("app_secret =", self.app_secret[:15] + "...(hidden)")
        print("account_no =", self.account_no)
        print("TOKEN_URL =", self.TOKEN_URL)
        print("base_url =", self.base_url)

        if self.mode == "REAL":
            print("[KISBroker] ENABLE_REAL_ORDER =", self.enable_real_order)

    # ===========================================================
    # Token 발급 + 캐싱
    # ===========================================================
    def get_token(self):
        """한국투자증권 토큰 발급 + 캐싱"""
        with token_lock:
            now = time.time()

            # 1) 파일 캐시 우선
            cached = get_cached_token()
            if cached:
                token = cached.get("access_token")
                expiry = cached.get("expiry", 0)
                if token and now < expiry - 60:
                    self.access_token = token
                    self.token_expiry = expiry
                    return token

            # 2) 메모리 캐시
            if self.access_token and now < self.token_expiry - 60:
                return self.access_token

            # 3) 새 토큰 발급
            headers = {"Content-Type": "application/json; charset=utf-8"}
            body = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }

            res = requests.post(self.TOKEN_URL, headers=headers, json=body)
            res.raise_for_status()

            data = res.json()
            token = data["access_token"]
            expiry = now + 3500  # 약 1시간

            self.access_token = token
            self.token_expiry = expiry

            print("\n[DEBUG] NEW ACCESS TOKEN ISSUED:")
            print(token)
            print("--------------------------------------------------")

            save_cached_token({"access_token": token, "expiry": expiry})
            return token

    # ===========================================================
    # 공통 헤더 생성
    # ===========================================================
    def _build_headers(self, tr_id="", include_content_type=False):
        """
        GET → Content-Type 없음
        POST → Content-Type 필수
        """
        token = self.get_token()

        headers = {
            "authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "N" if self.mode == "VTS" else "P",
        }

        if include_content_type:
            headers["Content-Type"] = "application/json; charset=utf-8"

        return headers

    # ===========================================================
    # 국내 현재가 조회
    # ===========================================================
    def get_price(self, symbol: str) -> float:
        headers = self._build_headers("FHKST01010100", include_content_type=False)
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol
        }

        r = requests.get(url, headers=headers, params=params)
        try:
            r.raise_for_status()
        except Exception:
            print("\n[국내 시세 조회 오류]", symbol)
            print("RESPONSE:", r.text)
            return 0.0

        return float(r.json()["output"]["stck_prpr"])

    # ===========================================================
    # 국내 잔고 조회
    # ===========================================================
    def get_balance(self):
        """
        REAL: TTTC8434R
        VTS : VTTC2472R
        ※ output2 구조가 dict 또는 list 로 내려오므로 자동 보정 필요
        """
        tr_id = "VTTC2472R" if self.mode == "VTS" else "TTTC8434R"
        headers = self._build_headers(tr_id, include_content_type=False)

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"

        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        r = requests.get(url, headers=headers, params=params)
        try:
            r.raise_for_status()
        except Exception:
            print("\n[국내 잔고 조회 오류]", r.text)
            return None

        data = r.json()
        out_raw = data.get("output2", {})

        # output2 구조 자동 보정
        if isinstance(out_raw, list):
            out = out_raw[0] if len(out_raw) > 0 else {}
        elif isinstance(out_raw, dict):
            out = out_raw
        else:
            out = {}

        return {
            "total_equity": float(out.get("tot_evlu_amt", 0)),
            "cash": float(out.get("dnca_tot_amt", 0)),
            "pnl_total": float(out.get("evlu_pfls_smtl_amt", 0)),
        }

    # ===========================================================
    # 국내 보유 종목 조회
    # ===========================================================
    def get_positions(self):
        """
        한국투자증권 공식 권장 방식:
        보유 종목 = 잔고조회(inquire-balance) 의 output1 을 사용
        """
        tr_id = "VTTC2472R" if self.mode == "VTS" else "TTTC8434R"
        headers = self._build_headers(tr_id, include_content_type=False)

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"

        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        r = requests.get(url, headers=headers, params=params)
        try:
            r.raise_for_status()
        except:
            print("\n[국내 보유 종목 조회 오류]", r.text)
            return []

        data = r.json()
        out_raw = data.get("output1", [])

        # output1 형식 보정
        if isinstance(out_raw, dict):
            out_list = [out_raw]
        elif isinstance(out_raw, list):
            out_list = out_raw
        else:
            out_list = []

        positions = []
        for row in out_list:
            positions.append({
                "symbol": row.get("pdno"),
                "qty": float(row.get("hldg_qty", 0)),
                "avg_price": float(row.get("pchs_avg_pric", 0)),
                "valuation": float(row.get("evlu_amt", 0)),
                "pnl": float(row.get("evlu_pfls_amt", 0)),
            })

        return positions

    # ===========================================================
    # 국내 매수 (POST)
    # ===========================================================
    def buy(self, symbol: str, qty: int, price: float = 0.0, order_type="03"):
        tr_id = "VTTC0802U" if self.mode == "VTS" else "TTTC0802U"
        headers = self._build_headers(tr_id, include_content_type=True)

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"

        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": symbol,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price if order_type == "00" else "0"),
        }

        # 실전주문 보호
        if self.mode == "REAL" and not self.enable_real_order:
            print("\n[REAL BUY SIMULATION] (실제 주문 전송 없음)")
            print("BODY:", body)
            return {"status": "SIMULATED", "body": body}

        r = requests.post(url, headers=headers, json=body)
        try:
            r.raise_for_status()
        except Exception:
            print("\n[국내 매수 주문 오류]", r.text)
            return None

        print("\n[국내 매수 주문 성공]")
        return r.json()

    # ===========================================================
    # 국내 매도 (POST)
    # ===========================================================
    def sell(self, symbol: str, qty: int, price: float = 0.0, order_type="03"):
        tr_id = "VTTC0801U" if self.mode == "VTS" else "TTTC0801U"
        headers = self._build_headers(tr_id, include_content_type=True)

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"

        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": symbol,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price if order_type == "00" else "0"),
        }

        if self.mode == "REAL" and not self.enable_real_order:
            print("\n[REAL SELL SIMULATION] (실제 주문 전송 없음)")
            print("BODY:", body)
            return {"status": "SIMULATED", "body": body}

        r = requests.post(url, headers=headers, json=body)
        try:
            r.raise_for_status()
        except Exception:
            print("\n[국내 매도 주문 오류]", r.text)
            return None

        print("\n[국내 매도 주문 성공]")
        return r.json()
