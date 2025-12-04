# src/core/app_context.py
import os
from pathlib import Path

from core.config_loader import load_settings
from brokers.kis_broker import KISBroker
from sheets.google_client import GoogleSheetsClient
from sheets.schema_loader import SchemaRegistry

from sheets.dt_report_repo import DTReportRepository
from sheets.position_repo import PositionRepository
from sheets.history_repo import HistoryRepository

from engine.portfolio_engine import PortfolioEngine


class AppContext:
    """
    시스템의 모든 주요 구성 요소를 초기화하고 보관하는 핵심 컨텍스트 클래스.
    - Google Sheets 연결
    - Schema 로드
    - Config Sheet 값 로드 (KIS_MODE 포함)
    - Broker(KIS), Repository, PortfolioEngine 초기화
    """

    def __init__(self, root_dir: Path):
        # ============================================================
        # 1. 기본 경로 설정
        # ============================================================
        self.root_dir = root_dir
        self.config_dir = root_dir / "config"

        # ============================================================
        # 2. settings.json 및 기타 설정파일 로드
        # ============================================================
        self.settings = load_settings(self.config_dir)

        # ============================================================
        # 3. Google Sheets 연결
        # ============================================================
        sheet_key = os.getenv("GOOGLE_SHEET_KEY")
        cred_file = os.getenv("GOOGLE_CREDENTIALS_FILE")

        self.gs = GoogleSheetsClient(sheet_key, cred_file)
        self.gs.connect()

        # ============================================================
        # 4. JSON 스키마 로드 (시트 구조 정의)
        # ============================================================
        schema_path = self.config_dir / "auto_trading_system_v2.1.schema.json"
        self.schema = SchemaRegistry(schema_path)

        # ============================================================
        # 5. Google Sheets → KIS_MODE 우선 적용
        #    SYSTEM_CONFIG 시트 C92에 위치한 값이 최우선 모드
        # ============================================================
        kis_mode_from_sheet = None
        try:
            kis_mode_from_sheet = self.gs.read_range("Config", "C92")[0][0]
            if kis_mode_from_sheet:
                kis_mode_from_sheet = str(kis_mode_from_sheet).strip().upper()
        except Exception:
            pass

        # ① 시트에서 읽힌 모드가 유효하면 우선 적용
        if kis_mode_from_sheet in ("VTS", "REAL"):
            self.kis_mode = kis_mode_from_sheet
        else:
            # ② 그렇지 않으면 .env의 KIS_MODE 사용
            self.kis_mode = os.getenv("KIS_MODE", "VTS").upper()

        print(f"[AppContext] KIS_MODE = {self.kis_mode}")

        # ============================================================
        # 6. KIS Broker 초기화
        #    (모드 정보를 넘겨주어 실전/모의 계좌/키 자동 스위칭)
        # ============================================================
        self.broker = KISBroker(mode=self.kis_mode)

        # ============================================================
        # 7. Repository 초기화 (DT_Report / Position / History)
        # ============================================================
        self.dt_report = DTReportRepository(self.schema, self.gs)
        self.position_repo = PositionRepository(self.schema, self.gs)
        self.history_repo = HistoryRepository(self.schema, self.gs)

        # ============================================================
        # 8. Position Sheet → initial_cash 읽기
        #    스키마의 "Position" 블록 Summary 정보를 기반으로 셀주소 자동 탐색
        # ============================================================
        pos_schema = self.schema.get("Position")

        # Summary 블록에서 initial_equity_investment 셀 주소 확보
        initial_cash_cell = pos_schema.blocks["Summary"]["initial_equity_investment"]

        # Google Sheet로부터 실제 값 읽기
        raw_value = self.gs.read_range("Position", initial_cash_cell)[0][0]

        try:
            # 세 자리 콤마 제거 후 float 변환
            initial_cash = float(str(raw_value).replace(",", "").strip())
        except Exception:
            initial_cash = 0.0

        print(f"[AppContext] Initial Cash Loaded: {initial_cash}")

        # ============================================================
        # 9. PortfolioEngine 초기화
        # ============================================================
        self.portfolio = PortfolioEngine(
            broker=self.broker,
            position_repo=self.position_repo,
            dt_repo=self.dt_report,
            initial_cash=initial_cash
        )
