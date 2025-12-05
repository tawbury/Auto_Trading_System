# src/core/app_context.py

import os
from pathlib import Path

from core.config_loader import load_settings
from brokers.kis_broker import KISBroker

from sheets.google_client import GoogleSheetsClient
from sheets.schema_registry import SchemaRegistry
from sheets.dt_report_repository import DTReportRepository
from sheets.position_repository import PositionRepository
from sheets.history_repository import HistoryRepository

from engine.portfolio_engine import PortfolioEngine

# TradingEngine 관련
from engine.trading.order_validator import OrderValidator
from engine.trading.position_sizer import PositionSizer
from engine.trading.order_executor import OrderExecutor
from engine.trading.trading_engine import TradingEngine

# 가격 조회 서비스 (broker → price_service)
from brokers.price_service import PriceService


class AppContext:
    """
    시스템 전체 구성요소를 초기화하는 핵심 컨텍스트.
    - Google Sheets 연결
    - Schema 로드
    - Repository 생성
    - Broker 생성(KIS)
    - PortfolioEngine 생성
    - TradingEngine 생성(신규)
    """

    def __init__(self, root_dir: Path):

        # ------------------------------------------------------------
        # 1. 기본 경로 설정
        # ------------------------------------------------------------
        self.root_dir = root_dir
        self.config_dir = root_dir / "config"

        # ------------------------------------------------------------
        # 2. settings.json 로드
        # ------------------------------------------------------------
        self.settings = load_settings(self.config_dir)

        # ------------------------------------------------------------
        # 3. Google Sheets 연결
        # ------------------------------------------------------------
        sheet_key = os.getenv("GOOGLE_SHEET_KEY")
        cred_file = os.getenv("GOOGLE_CREDENTIALS_FILE")

        self.gs = GoogleSheetsClient(sheet_key, cred_file)
        self.gs.connect()

        # ------------------------------------------------------------
        # 4. 스키마 로드
        # ------------------------------------------------------------
        schema_path = self.config_dir / "auto_trading_system.schema.json"
        self.schema = SchemaRegistry(schema_path)

        # ------------------------------------------------------------
        # 5. KIS_MODE 설정 (시트 값 > .env)
        # ------------------------------------------------------------
        try:
            kis_mode_from_sheet = self.gs.read_range("Config", "C92")[0][0].strip().upper()
        except Exception:
            kis_mode_from_sheet = None

        if kis_mode_from_sheet in ("VTS", "REAL"):
            self.kis_mode = kis_mode_from_sheet
        else:
            self.kis_mode = os.getenv("KIS_MODE", "VTS").upper()

        print(f"[AppContext] KIS_MODE = {self.kis_mode}")

        # ------------------------------------------------------------
        # 6. Broker 초기화
        # ------------------------------------------------------------
        self.broker = KISBroker(mode=self.kis_mode)

        # PriceService 생성 (broker 기반)
        self.price_service = PriceService(self.broker)

        # ------------------------------------------------------------
        # 7. Repository 초기화
        # ------------------------------------------------------------
        self.dt_repo = DTReportRepository(self.schema, self.gs)
        self.position_repo = PositionRepository(self.schema, self.gs)
        self.history_repo = HistoryRepository(self.schema, self.gs)

        # ------------------------------------------------------------
        # 8. Position 시트에서 초기자본 읽기
        # ------------------------------------------------------------
        pos_schema = self.schema.get("Position")
        initial_cash_cell = pos_schema.blocks["Summary"]["initial_equity_investment"]

        try:
            raw_value = self.gs.read_range("Position", initial_cash_cell)[0][0]
            initial_cash = float(str(raw_value).replace(",", "").strip())
        except Exception:
            initial_cash = 0.0

        print(f"[AppContext] Initial_Cash Loaded = {initial_cash}")

        # ------------------------------------------------------------
        # 9. PortfolioEngine 초기화
        # ------------------------------------------------------------
        self.portfolio = PortfolioEngine(
            broker=self.broker,
            position_repo=self.position_repo,
            dt_repo=self.dt_repo,
            initial_cash=initial_cash,
        )

        # ============================================================
        # ★ 10. TradingEngine 구성 요소 생성 (신규 추가)
        # ============================================================

        # A) OrderValidator
        self.order_validator = OrderValidator(
            risk_engine=None,  # RiskEngine 연결 시 여기에 주입
            pos_repo=self.position_repo,
            config=self.settings.get("validator", {})
        )

        # B) PositionSizer
        self.position_sizer = PositionSizer(
            price_service=self.price_service,
            history_repo=self.history_repo,
            config=self.settings.get("sizer", {})
        )

        # C) OrderExecutor
        self.order_executor = OrderExecutor(broker=self.broker)

        # D) TradingEngine 생성
        self.trading_engine = TradingEngine(
            dt_repo=self.dt_repo,
            pos_repo=self.position_repo,
            hist_repo=self.history_repo,
            validator=self.order_validator,
            sizer=self.position_sizer,
            executor=self.order_executor
        )

        print("[AppContext] TradingEngine 초기화 완료")
