"""
Paper broker only. Mimics live broker interface.
Tracks slippage, fills, fees, inventory, and realized PnL.
"""
import uuid
import time
from typing import Dict, Any
from .interface import IBroker

class PaperBroker(IBroker):
    def __init__(self, initial_balance_usd: float = 10_000.0, fee_rate_bps: float = 5.0, slippage_bps: float = 2.0):
        self.cash_balance_usd = initial_balance_usd
        self.fee_rate_bps = fee_rate_bps
        self.slippage_bps = slippage_bps
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history = []

    def get_balance(self) -> float:
        return self.cash_balance_usd

    def get_position(self, symbol: str) -> float:
        pos = self.positions.get(symbol)
        return pos["size_usd"] if pos else 0.0

    def place_order(self, symbol: str, side: str, size_usd: float, price: float) -> Dict[str, Any]:
        if size_usd > self.cash_balance_usd:
            raise ValueError(f"Insufficient funds: required ${size_usd:.2f}, balance ${self.cash_balance_usd:.2f}")

        slip_multiplier = (1.0 + (self.slippage_bps / 10_000.0)) if side == "buy" else (1.0 - (self.slippage_bps / 10_000.0))
        fill_price = price * slip_multiplier
        fee_usd = size_usd * (self.fee_rate_bps / 10_000.0)

        order_id = str(uuid.uuid4())[:8]
        fill_record = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "size_usd": size_usd,
            "req_price": price,
            "fill_price": fill_price,
            "fee_usd": fee_usd,
            "timestamp": int(time.time() * 1000)
        }
        self.trade_history.append(fill_record)
        self.cash_balance_usd -= fee_usd

        self.positions[symbol] = {
            "symbol": symbol,
            "side": side,
            "size_usd": size_usd,
            "entry_price": fill_price,
            "entry_time": fill_record["timestamp"]
        }
        return fill_record

    def cancel_all_orders(self, symbol: str) -> bool:
        return True

    def close_position(self, symbol: str, current_price: float) -> Dict[str, Any]:
        pos = self.positions.pop(symbol, None)
        if not pos:
            return {"status": "no_position"}

        side = pos["side"]
        entry_price = pos["entry_price"]
        size_usd = pos["size_usd"]
        slip_mult = (1.0 - (self.slippage_bps / 10_000.0)) if side == "buy" else (1.0 + (self.slippage_bps / 10_000.0))
        exit_price = current_price * slip_mult
        gross_return = (exit_price - entry_price) / entry_price if side == "buy" else (entry_price - exit_price) / entry_price
        pnl_usd = size_usd * gross_return
        exit_fee = size_usd * (self.fee_rate_bps / 10_000.0)
        net_pnl = pnl_usd - exit_fee
        self.cash_balance_usd += (size_usd + net_pnl)

        return {
            "symbol": symbol,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "net_pnl": net_pnl,
            "exit_fee": exit_fee
        }
