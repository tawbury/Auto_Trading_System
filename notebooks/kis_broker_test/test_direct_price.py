import os
import pathlib
import requests
from dotenv import load_dotenv

# Load env
ROOT = pathlib.Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

REAL_URL = os.getenv("REAL_BASE_URL")
REAL_KEY = os.getenv("REAL_APP_KEY")
REAL_SECRET = os.getenv("REAL_APP_SECRET")

print("=== DIRECT PRICE API TEST ===")
print("REAL_URL:", REAL_URL)

# ---------------------------------
# 1) Token 발급
# ---------------------------------
token_res = requests.post(
    REAL_URL + "/oauth2/tokenP",
    headers={"Content-Type": "application/json"},
    json={
        "grant_type": "client_credentials",
        "appkey": REAL_KEY,
        "appsecret": REAL_SECRET
    }
)

print("\nTOKEN RESPONSE:")
print(token_res.text)

token = token_res.json().get("access_token")
if not token:
    print("TOKEN 발급 실패")
    exit()

# ---------------------------------
# 2) 발급된 토큰으로 현재가 조회
# ---------------------------------
price_url = REAL_URL + "/uapi/domestic-stock/v1/quotations/inquire-price"

headers = {
    "authorization": "Bearer " + token,
    "appKey": REAL_KEY,
    "appSecret": REAL_SECRET,
    "tr_id": "FHKST01010100",
    "custtype": "N",
}

params = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_INPUT_ISCD": "005930"
}

price_res = requests.get(price_url, headers=headers, params=params)

print("\nPRICE RESPONSE:")
print(price_res.text)
