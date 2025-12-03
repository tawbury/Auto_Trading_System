# src/brokers/broker_interface.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BrokerInterface(ABC):
    @abstractmethod
    def buy(self, symbol: str, qty: int, **kwargs) -> Dict[str, Any]:
        ...

    @abstractmethod
    def sell(self, symbol: str, qty: int, **kwargs) -> Dict[str, Any]:
        ...

    @abstractmethod
    def get_price(self, symbol: str) -> float:
        ...

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        ...
