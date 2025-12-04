# src/engine/portfolio_engine.py

from typing import Dict, List, Any
from brokers.broker_interface import BrokerInterface
from sheets.position_repo import PositionRepository
from sheets.dt_report_repo import DTReportRepository


class PortfolioEngine:
    """
    포트폴리오 전체 상태를 평가하는 핵심 엔진.

    기능 요약:
    - Position Sheet(보유종목) 로딩
    - DT_Report 기반 평균단가 재계산 (보정)
    - KISBroker 기반 현재가 조회(get_price)
    - KR / US / HK 통합 시장 구조 유지
    - 해외 시세는 현재 비활성(0) 처리하지만 구조는 그대로 보존
    """

    def __init__(
        self,
        broker: BrokerInterface,
        position_repo: PositionRepository,
        dt_repo: DTReportRepository,
        initial_cash: float = 0.0
    ):
        self.broker = broker
        self.position_repo = position_repo
        self.dt_repo = dt_repo
        self.initial_cash = initial_cash

    # ------------------------------------------------------------
    # float 변환 안전 처리
    # ------------------------------------------------------------
    @staticmethod
    def _to_float(value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)

        s = str(value).replace(",", "").strip()
        if s == "":
            return 0.0

        try:
            return float(s)
        except ValueError:
            return 0.0

    # ------------------------------------------------------------
    # DT_Report 기반 평균단가 (보정)
    # ------------------------------------------------------------
    def _calculate_avg_price_from_dt(self, symbol: str) -> float:
        records = self.dt_repo.load_all()

        total_qty = 0.0
        total_amount = 0.0

        for r in records:
            if r.get("symbol") != symbol:
                continue

            if (r.get("side") or "").upper() != "BUY":
                continue

            qty = self._to_float(r.get("qty"))
            amount = self._to_float(r.get("amount_local"))

            total_qty += qty
            total_amount += amount

        if total_qty <= 0:
            return 0.0

        return total_amount / total_qty

    # ------------------------------------------------------------
    # 포지션 개별 평가
    # ------------------------------------------------------------
    def evaluate_positions(self) -> List[Dict]:
        """
        KR / US / HK 를 모두 지원하는 형태로 구조 유지.
        해외는 현재 시세 비활성(0 처리).
        """
        positions = self.position_repo.load_all()
        evaluated = []

        for p in positions:
            symbol = p.get("symbol")
            if not symbol:
                continue

            qty = self._to_float(p.get("qty"))
            if qty <= 0:
                continue

            market = (p.get("market") or "").upper()
            avg_price = self._to_float(p.get("avg_price"))

            if avg_price <= 0:
                avg_price = self._calculate_avg_price_from_dt(symbol)

            # ----------------------------------------
            # 시장별 현재가 조회
            # ----------------------------------------
            if market == "KR":
                # 국내: 정상 작동
                current_price = self.broker.get_price(symbol)

            elif market in ("US", "NASDAQ", "NYSE", "AMEX"):
                # 해외: 구조는 유지, 현재는 0 반환
                # (실전 전환 / 외부 API 연동 시 활성화)
                # current_price = self.broker.get_overseas_price("NASD", symbol)
                current_price = 0.0

            elif market == "HK":
                # 홍콩 시장 기능도 유지
                # current_price = self.broker.get_overseas_price("HKG", symbol)
                current_price = 0.0

            else:
                # 정의되지 않은 시장
                current_price = 0.0

            valuation = current_price * qty
            cost = avg_price * qty
            pnl = valuation - cost

            evaluated.append({
                "symbol": symbol,
                "qty": qty,
                "avg_price": avg_price,
                "current_price": current_price,
                "valuation": valuation,
                "cost": cost,
                "pnl": pnl,
                "market": market
            })

        return evaluated

    # ------------------------------------------------------------
    # 현금 잔고 계산
    # ------------------------------------------------------------
    def calculate_cash_balance(self) -> float:
        """
        initial_cash + SELL - BUY
        (DT_Report 기준)
        """
        records = self.dt_repo.load_all()

        buy_amount = 0.0
        sell_amount = 0.0

        for r in records:
            side = (r.get("side") or "").upper()
            net = self._to_float(r.get("net_amount_krw"))

            if side == "BUY":
                buy_amount += net
            elif side == "SELL":
                sell_amount += net

        return self.initial_cash + sell_amount - buy_amount

    # ------------------------------------------------------------
    # 전체 포트폴리오 평가 결과
    # ------------------------------------------------------------
    def build_portfolio_state(self) -> Dict:
        positions = self.evaluate_positions()

        stock_equity = sum(p["valuation"] for p in positions)
        cost_basis = sum(p["cost"] for p in positions)
        total_pnl = sum(p["pnl"] for p in positions)

        cash_balance = self.calculate_cash_balance()
        total_equity = stock_equity + cash_balance

        exposure = stock_equity / total_equity if total_equity > 0 else 0
        cash_ratio = cash_balance / total_equity if total_equity > 0 else 0

        return {
            "total_equity": total_equity,
            "stock_equity": stock_equity,
            "cash_balance": cash_balance,
            "exposure": exposure,
            "cash_ratio": cash_ratio,
            "holdings_count": len(positions),
            "positions": positions,
            "pnl": total_pnl,
            "cost_basis": cost_basis
        }
