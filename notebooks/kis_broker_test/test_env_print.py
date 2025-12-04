import os
import pathlib
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[2]
env_path = ROOT / ".env"

print("ENV_PATH:", env_path)
load_dotenv(env_path)

# 모드
print("KIS_MODE =", os.getenv("KIS_MODE"))
print("ENABLE_REAL_ORDER =", os.getenv("ENABLE_REAL_ORDER"))

# REAL 값
print("REAL_APP_KEY =", os.getenv("REAL_APP_KEY"))
print("REAL_APP_SECRET =", os.getenv("REAL_APP_SECRET"))
print("REAL_ACCOUNT_NO =", os.getenv("REAL_ACCOUNT_NO"))
print("REAL_ACNT_PRDT_CD =", os.getenv("REAL_ACNT_PRDT_CD"))
print("REAL_BASE_URL =", os.getenv("REAL_BASE_URL"))

# VTS 값
print("VTS_BASE_URL =", os.getenv("VTS_BASE_URL"))
