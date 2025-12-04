import os
import pathlib
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[2]

print("ROOT =", ROOT)
print("ENV PATH =", ROOT / ".env")
print("ENV EXISTS =", (ROOT / ".env").exists())

load_dotenv(ROOT / ".env")

print("APP_KEY =", os.getenv("APP_KEY"))
print("APP_SECRET =", os.getenv("APP_SECRET"))
print("ACCOUNT_NO =", os.getenv("ACCOUNT_NO"))
print("KIS_MODE =", os.getenv("KIS_MODE"))
