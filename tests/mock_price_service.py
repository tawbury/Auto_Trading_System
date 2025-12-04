# tests/mock_price_service.py

class MockPriceService:
    """
    테스트용 price_service
    어떤 종목이든 항상 70,000원으로 반환
    """
    def get_live_price(self, symbol, market):
        return 70000
