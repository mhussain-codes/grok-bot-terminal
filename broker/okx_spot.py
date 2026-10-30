"""
OKX Spot Broker implementing standard IBroker interface.
Routes spot orders directly to OKX using authenticated HMAC-SHA256.
"""
from typing import Dict, Any
from .interface import IBroker
from ..okx_client import OKXSpotClient

class OKXSpotBroker(IBroker):
    def __init__(self, api_key: str, secret_key: str, passphrase: str):
        self.client = OKXSpotClient(api_key, secret_key, passphrase)

    def get_balance(self) -> float:
        acc = self.client.get_account_balance()
        return acc.get("total_equity_usd", 0.0)

    def get_position(self, symbol: str) -> float:
        # For spot, returns base asset balance
        base_asset = symbol.split("-")[0]
        acc = self.client.get_account_balance()
        return acc.get("balances", {}).get(base_asset, 0.0)

    def place_order(self, symbol: str, side: str, size_usd: float, price: float) -> Dict[str, Any]:
        """Places a SPOT order on OKX."""
        # For OKX cash market buy order, sz is USDT amount
        res = self.client.place_spot_order(symbol=symbol, side=side, sz=str(round(size_usd, 2)))
        return res

    def cancel_all_orders(self, symbol: str) -> bool:
        return True

    def close_position(self, symbol: str, current_price: float) -> Dict[str, Any]:
        base_asset = symbol.split("-")[0]
        pos_size = self.get_position(symbol)
        if pos_size > 0:
            return self.client.place_spot_order(symbol=symbol, side="sell", sz=str(pos_size))
        return {"status": "no_position"}
