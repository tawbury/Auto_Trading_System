from brokers.kis_broker import KISBroker

print("=== KISBroker Debug Test ===")

b = KISBroker()

# 가격 조회 호출 시 내부 요청을 직접 출력하도록 수정한 버전
price = b.get_price("005930")
print("PRICE =", price)
