# src/brokers/test_direct_balance.py
# 실전 계좌 잔고조회 직접 REST 테스트
print("### LOADED FILE:", __file__)

import os
import requests
from dotenv import load_dotenv

load_dotenv()

REAL_URL = os.getenv("REAL_BASE_URL")
APP_KEY = os.getenv("REAL_APP_KEY")
APP_SECRET = os.getenv("REAL_APP_SECRET")
ACCOUNT_NO = os.getenv("REAL_ACCOUNT_NO")
ACNT_PRDT_CD = os.getenv("REAL_ACNT_PRDT_CD", "01")

# 1) 토큰 발급
token_url = f"{REAL_URL}/oauth2/tokenP"

token_headers = {
    "Content-Type": "application/json; charset=utf-8"
}

body = {
    "grant_type": "client_credentials",
    "appkey": APP_KEY,
    "appsecret": APP_SECRET
}

token_res = requests.post(token_url, headers=token_headers, json=body).json()
token = token_res["access_token"]

print("=== DIRECT BALANCE API TEST ===")
print("TOKEN:", token)

# 2) 잔고조회 (GET)
tr_id = "TTTC8434R"   # 실전 TR ID (핵심)

headers = {
    "authorization": f"Bearer {token}",
    "appKey": APP_KEY,
    "appSecret": APP_SECRET,
    "tr_id": tr_id,
    "custtype": "P"       # 실전 계좌 custtype
}

url = f"{REAL_URL}/uapi/domestic-stock/v1/trading/inquire-balance"

params = {
    "CANO": ACCOUNT_NO,
    "ACNT_PRDT_CD": ACNT_PRDT_CD,
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


res = requests.get(url, headers=headers, params=params)
print("BALANCE RESPONSE:")
print(res.text)
