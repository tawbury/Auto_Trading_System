# src/engine/trading/models.py

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


# ============================================================
# ENUM DEFINITIONS
# ============================================================

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class MarketType(str, Enum):
    KR = "KR"
    US = "US"
    HK = "HK"
    FX = "FX"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


# ============================================================
# 1) TradeSignal
#    전략/조건식에서 올라오는 "시그널" 데이터
# ============================================================

@dataclass
class TradeSignal:
    symbol: str
    market: MarketType
    side: OrderSide
    strategy: str                      # 예: "GC_RSI", "BB", "ATR", "COND01"
    priority: int = 0                  # 추후 우선순위큐 활용 시 사용
    timestamp: datetime = field(default_factory=datetime.utcnow)
    meta: Optional[Dict[str, Any]] = None


# ============================================================
# 2) OrderRequest
#    TradingEngine가 실제 브로커로 내보내는 구체적 주문 요청
# ============================================================

@dataclass
class OrderRequest:
    symbol: str
    market: MarketType
    side: OrderSide
    qty: float
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None      # 시장가일 경우 None
    strategy: Optional[str] = ""
    broker: Optional[str] = ""         # "KIS", "KIWOOM_REST", "KIWOOM_COM"
    slippage_limit: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ============================================================
# 3) OrderResult
#    브로커 체결 정보 (DT_Report에 기록할 데이터 완비)
# ============================================================

@dataclass
class OrderResult:
    order_id: str
    symbol: str
    market: MarketType
    side: OrderSide
    qty: float
    avg_price: float                   # 체결가(평균가)
    fee_tax: float                     # 수수료/세금
    amount_local: float                # 현지 통화 기준 체결금액
    currency: str                      # "KRW", "USD", "HKD", "JPY"
    fx_rate: float                     # 환율
    amount_krw: float                  # 원화 기준 체결금액
    broker: str                        # "KIS", "KIWOOM_REST", "KIWOOM_COM"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    raw: Optional[Dict[str, Any]] = None  # 브로커 원본 JSON 응답(Optional)
