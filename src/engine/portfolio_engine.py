# src/engine/portfolio_engine.py

from typing import Dict, List, Any
from brokers.broker_interface import BrokerInterface
from sheets.position_repo import PositionRepository
from sheets.dt_report_repo import DTReportRepository
from brokers.price_service import PriceService


class PortfolioEngine:
    """
    포트폴리오 전체 상태 계산
    - KR / US / HK 현재가 연동
    - 평가금액, 총자산, 노출도, 현금비중 계산
    """

    def __init__(self,
                 broker: BrokerInterface,
                 position_repo: PositionRepository,
                 dt_repo: DTReportRepository,
                 initial_cash: float = 0.0):

        self.broker = broker
        self.position_repo = position_repo
        self.dt_repo = dt_repo
        self.initial_cash = initial_cash

        # 해외/국내 통합 가격 조회 서비스
        self.price_service = PriceService(broker)

    # Float 변환 안전 처리
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

    # DT_Report 기반 평균 단가 계산
    def _calculate_avg_price_from_dt(self, symbol: str) -> float:
        records = self.dt_repo.load_all()

        total_qty = 0.0
        total_amount = 0.0

        for r in records:
            if r.get("symbol") != symbol:
                continue

            side = (r.get("side") or "").upper()
            if side != "BUY":
                continue

            qty = self._to_float(r.get("qty"))
            amount_local = self._to_float(r.get("amount_local"))

            total_qty += qty
            total_amount += amount_local

        if total_qty <= 0:
            return 0.0

        return total_amount / total_qty

    # -----------------------------
    # 포지션 평가
    # -----------------------------
    def evaluate_positions(self) -> List[Dict]:
        positions = self.position_repo.load_all()
        evaluated = []

        for p in positions:
            symbol = p.get("symbol")
            if not symbol:
                continue

            qty = self._to_float(p.get("qty"))
            if qty <= 0:
                continue

            market = p.get("market", "")
            avg_price = self._to_float(p.get("avg_price"))

            if avg_price <= 0:
                avg_price = self._calculate_avg_price_from_dt(symbol)

            # **KR/US/HK 통합 현재가 조회**
            current_price = self.price_service.get_live_price(symbol, market)

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

    # -----------------------------
    # 현금 계산
    # -----------------------------
    def calculate_cash_balance(self) -> float:
        records = self.dt_repo.load_all()

        buy_amount = 0.0
        sell_amount = 0.0

        for r in records:
            side = (r.get("side") or "").upper()
            net_amount = self._to_float(r.get("net_amount_krw"))

            if side == "BUY":
                buy_amount += net_amount
            elif side == "SELL":
                sell_amount += net_amount

        return self.initial_cash + sell_amount - buy_amount

    # -----------------------------
    # 최종 포트폴리오 상태
    # -----------------------------
    def build_portfolio_state(self) -> Dict:
        positions = self.evaluate_positions()

        stock_equity = sum(p["valuation"] for p in positions)
        cost_basis = sum(p["cost"] for p in positions)
        total_pnl = sum(p["pnl"] for p in positions)

        cash_balance = self.calculate_cash_balance()
        total_equity = stock_equity + cash_balance

        exposure = (stock_equity / total_equity) if total_equity > 0 else 0.0
        cash_ratio = (cash_balance / total_equity) if total_equity > 0 else 0.0

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
