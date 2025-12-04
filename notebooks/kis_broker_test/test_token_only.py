from src.brokers.kis_broker import KISBroker

print("=== TOKEN ONLY TEST ===")
b = KISBroker()

token = b.get_token()

print("\n=== FULL TOKEN ===")
print(token)
