import gspread
from pathlib import Path
from typing import List


class GoogleSheetsClient:
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        """
        ATS용 Google Sheets Client

        parameters
        ----------
        credentials_path : service account json
        spreadsheet_id   : spreadsheet의 고유 ID
        """
        self.spreadsheet_id = spreadsheet_id
        self.gc = gspread.service_account(filename=credentials_path)
        self.sh = self.gc.open_by_key(self.spreadsheet_id)

    def read_range(self, worksheet_name: str, range_a1: str) -> List[List]:
        ws = self.sh.worksheet(worksheet_name)
        return ws.get(range_a1)
