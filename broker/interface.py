from abc import ABC, abstractmethod
from typing import Dict, Any

class IBroker(ABC):
    @abstractmethod
    def get_balance(self) -> float:
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> float:
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: str, size_usd: float, price: float) -> Dict[str, Any]:
        pass

    @abstractmethod
    def cancel_all_orders(self, symbol: str) -> bool:
        pass

    @abstractmethod
    def close_position(self, symbol: str, current_price: float) -> Dict[str, Any]:
        pass
