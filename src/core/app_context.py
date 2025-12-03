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
    def __init__(self, root_dir: Path):
        # 기본 경로
        self.root_dir = root_dir
        self.config_dir = root_dir / "config"

        # settings 로드
        self.settings = load_settings(self.config_dir)

        # Google Sheets 연결
        sheet_key = os.getenv("GOOGLE_SHEET_KEY")
        cred_file = os.getenv("GOOGLE_CREDENTIALS_FILE")

        self.gs = GoogleSheetsClient(sheet_key, cred_file)
        self.gs.connect()

        # JSON 스키마 로드
        schema_path = self.config_dir / "auto_trading_system_v2.1.schema.json"
        self.schema = SchemaRegistry(schema_path)

        # Repository 초기화
        self.dt_report = DTReportRepository(self.schema, self.gs)
        self.position_repo = PositionRepository(self.schema, self.gs)
        self.history_repo = HistoryRepository(self.schema, self.gs)

        # -------------------- initial_cash 로드 --------------------

        pos_schema = self.schema.get("Position")

        # Summary 블록에서 initial_equity_investment 키 읽기
        initial_cash_addr = pos_schema.blocks["Summary"]["initial_equity_investment"]

        # Position 시트에서 셀값 읽기
        cell_value = self.gs.read_range("Position", initial_cash_addr)[0][0]

        # 변환
        try:
            initial_cash = float(str(cell_value).replace(",", "").strip())
        except:
            initial_cash = 0.0

        print("### DEBUG: initial_cash_addr =", initial_cash_addr)
        print("### DEBUG: initial_cash_str =", cell_value)
        print("### DEBUG: parsed initial_cash =", initial_cash)

        # ----------------------------------------------------------

        self.portfolio = PortfolioEngine(
            broker=KISBroker(),
            position_repo=self.position_repo,
            dt_repo=self.dt_report,
            initial_cash=initial_cash
        )

        self.broker = KISBroker()
