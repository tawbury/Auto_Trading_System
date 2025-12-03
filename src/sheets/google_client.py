# src/sheets/google_client.py
import gspread
from google.oauth2.service_account import Credentials


class GoogleSheetsClient:
    def __init__(self, spreadsheet_key: str, credentials_file: str):
        self.spreadsheet_key = spreadsheet_key
        self.credentials_file = credentials_file
        self.gc = None
        self.sh = None

    # ---------------------------------------------------------
    # 1) 구글 시트 연결
    # ---------------------------------------------------------
    def connect(self):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(
            self.credentials_file,
            scopes=scopes
        )
        self.gc = gspread.authorize(creds)
        self.sh = self.gc.open_by_key(self.spreadsheet_key)

    # ---------------------------------------------------------
    # 2) 워크시트 가져오기
    # ---------------------------------------------------------
    def get_sheet(self, name: str):
        if self.sh is None:
            raise Exception("GoogleSheetsClient is not connected.")
        return self.sh.worksheet(name)

    # ---------------------------------------------------------
    # 3) 특정 범위 읽기 (A1:C10)
    # ---------------------------------------------------------
    def read_range(self, name: str, a1_range: str):
        ws = self.get_sheet(name)
        return ws.get(a1_range)

    # ---------------------------------------------------------
    # 4) 특정 범위 쓰기
    # ---------------------------------------------------------
    def write_range(self, name: str, a1_range: str, values):
        ws = self.get_sheet(name)
        ws.update(a1_range, values)

    # ---------------------------------------------------------
    # 5) 시트 전체 읽기 (DT_Report 전체 로드용)
    # ---------------------------------------------------------
    def read_all(self, name: str):
        ws = self.get_sheet(name)
        return ws.get_all_values()
