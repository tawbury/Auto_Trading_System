# src/brokers/price_service.py

from brokers.kis_broker import KISBroker


class PriceService:
    """
    KR / US / HK 해외 현재가 통합 조회 서비스
    """
    def __init__(self, broker: KISBroker):
        self.broker = broker

    # 시장 코드 매핑
    EXCD = {
        "US": "NASD",
        "HK": "HKEX",
        "JP": "TSE"
    }

    def get_live_price(self, symbol: str, market: str) -> float:
        market = market.upper().strip()

        # 1) 국내 주식
        if market == "KR":
            return self.broker.get_price(symbol)

        # 2) 해외 주식
        if market in ("US", "HK", "JP"):
            exch_code = self.EXCD.get(market, None)
            if not exch_code:
                return 0.0

            return self.broker.get_overseas_price(exch_code, symbol)

        # 3) 그 외: 지원하지 않음
        return 0.0
