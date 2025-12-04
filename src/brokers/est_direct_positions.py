import os
import pathlib
import requests
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

REAL_URL = os.getenv("REAL_BASE_URL")
REAL_KEY = os.getenv("REAL_APP_KEY")
REAL_SECRET = os.getenv("REAL_APP_SECRET")
REAL_ACC = os.getenv("REAL_ACCOUNT_NO")
REAL_PRD = os.getenv("REAL_ACNT_PRDT_CD")

print("=== DIRECT POSITIONS TEST ===")

# Token 발급
token = requests.post(
    REAL_URL + "/oauth2/tokenP",
    headers={"Content-Type": "application/json"},
    json={"grant_type": "client_credentials",
          "appkey": REAL_KEY,
          "appsecret": REAL_SECRET}
).json()["access_token"]

headers = {
    "authorization": "Bearer " + token,
    "appKey": REAL_KEY,
    "appSecret": REAL_SECRET,
    "tr_id": "VTTC8448R",
    "custtype": "N"
}

params = {
    "CANO": REAL_ACC,
    "ACNT_PRDT_CD": REAL_PRD,
    "INQR_DVSN": "01",
    "CTX_AREA_FK200": "",
    "CTX_AREA_NK200": "",
}

url = REAL_URL + "/uapi/domestic-stock/v1/trading/inquire-balance-kr"

res = requests.get(url, headers=headers, params=params)

print("POSITIONS RESPONSE:")
print(res.text)
