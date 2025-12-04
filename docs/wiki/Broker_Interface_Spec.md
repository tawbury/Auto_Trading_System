# Broker Interface Spec

브로커 추상 클래스 정의:

필수 메서드:
- get_price(symbol)
- get_balance()
- get_positions()
- buy()
- sell()

실제 구현체는 [[KIS REST Broker]] 참고.
