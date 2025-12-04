# src/sheets/google_client.py
import gspread
from google.oauth2.service_account import Credentials


class GoogleSheetsClient:
    """
    Google Sheets 연결 및 범위 기반 읽기/쓰기 기능을 제공하는 클라이언트 클래스.
    스키마 기반 Config(Key-Value) 항목 자동 로딩 기능도 포함된다.
    """

    def __init__(self, spreadsheet_key: str, credentials_file: str):
        self.spreadsheet_key = spreadsheet_key
        self.credentials_file = credentials_file

        self.gc = None         # gspread client
        self.sh = None         # opened spreadsheet

    # ============================================================
    # 1) Google Sheet 연결
    # ============================================================
    def connect(self):
        """
        Google Service Account JSON 파일을 기반으로 시트에 연결.
        """
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

    # ============================================================
    # 2) 특정 워크시트 가져오기
    # ============================================================
    def get_sheet(self, name: str):
        """
        시트 이름으로 Worksheet 객체를 반환한다.
        """
        if self.sh is None:
            raise Exception("GoogleSheetsClient is not connected.")
        return self.sh.worksheet(name)

    # ============================================================
    # 3) 특정 범위 읽기 (A1:C10 등)
    # ============================================================
    def read_range(self, name: str, a1_range: str):
        """
        워크시트에서 A1 표기법 범위를 읽어 리스트 형식으로 반환.
        """
        ws = self.get_sheet(name)
        return ws.get(a1_range)

    # ============================================================
    # 4) 특정 범위 쓰기
    # ============================================================
    def write_range(self, name: str, a1_range: str, values):
        """
        주어진 2차원 리스트를 지정된 A1 범위에 기록.
        """
        ws = self.get_sheet(name)
        ws.update(a1_range, values)

    # ============================================================
    # 5) 시트 전체 읽기
    # ============================================================
    def read_all(self, name: str):
        """
        워크시트 전체를 이차원 리스트 형태로 반환.
        (DT_Report 등 전체 로딩용)
        """
        ws = self.get_sheet(name)
        return ws.get_all_values()

    # ============================================================
    # 6) Config Sheet (Key-Value) 읽기 — 스키마 기반 확장 가능
    # ============================================================
    def get_config_value(self, schema, key: str):
        """
        스키마에 등록된 Config Sheet의 'key' 항목을 자동으로 읽어온다.
        예)
            "KIS_MODE": {"value_cell": "C92", "description_cell": "D92"}

        Args:
            schema: SchemaRegistry 객체
            key:    스키마에 정의된 Key 문자열

        Returns:
            값이 존재하면 문자열로 반환, 없으면 None
        """
        try:
            cfg_schema = schema.sheets.get("Config")
            if not cfg_schema:
                return None

            # fields 배열에서 key에 해당하는 item 탐색
            field_item = None
            for item in cfg_schema.get("fields", []):
                if item.get("key") == key or item.get("field") == key:
                    field_item = item
                    break

            if not field_item:
                return None

            value_cell = field_item.get("value_cell")
            if not value_cell:
                return None

            ws = self.get_sheet("Config")
            raw = ws.acell(value_cell).value

            if raw is None:
                return None

            return str(raw).strip()

        except Exception:
            return None

    # ============================================================
    # 7) KIS_MODE 전용 Getter (스키마 기반)
    # ============================================================
    def get_kis_mode(self, schema):
        """
        스키마 정의에 따라 Config Sheet의 KIS_MODE를 자동으로 가져온다.
        - 스키마에 정의된 C92 좌표 값을 읽음.
        - 값이 없으면 None 반환.
        """
        mode = self.get_config_value(schema, "KIS_MODE")
        if mode:
            return mode.upper()
        return None

