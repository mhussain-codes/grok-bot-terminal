"""
Deterministic state builder that compresses raw market data into a compact snapshot
guaranteed to be under 400 tokens. Uses ONLY data timestamped prior to decision cutoff.
"""
from dataclasses import dataclass
import math
from typing import List, Dict, Any, Tuple

@dataclass(frozen=True)
class MarketSnapshot:
    mid: float
    spread_bps: float
    imbalance: float          # -1.0 (all ask) to +1.0 (all bid)
    realized_vol_bps: float
    ret_w1_bps: float         # 1-minute / fast return
    ret_w2_bps: float         # 5-minute / medium return
    ret_w3_bps: float         # 15-minute / slow return
    inventory_usd: float
    current_drawdown_bps: float
    decision_cutoff_ts: int   # Milliseconds epoch

    def to_compact_dict(self) -> Dict[str, Any]:
        """Serializes numbers with limited precision to stay well under 400 tokens."""
        return {
            "mid": round(self.mid, 6),
            "sp_bps": round(self.spread_bps, 2),
            "imb": round(self.imbalance, 3),
            "r_vol": round(self.realized_vol_bps, 2),
            "r_w1": round(self.ret_w1_bps, 2),
            "r_w2": round(self.ret_w2_bps, 2),
            "r_w3": round(self.ret_w3_bps, 2),
            "inv": round(self.inventory_usd, 2),
            "dd_bps": round(self.current_drawdown_bps, 2),
            "cutoff": self.decision_cutoff_ts
        }

def compute_snapshot(
    bids: List[Tuple[float, float]],            # (price, size)
    asks: List[Tuple[float, float]],            # (price, size)
    price_history: List[Tuple[int, float]],     # (ts, close_price) strictly <= cutoff_ts
    inventory_usd: float,
    peak_equity_usd: float,
    current_equity_usd: float,
    cutoff_ts: int
) -> MarketSnapshot:
    best_bid, bid_sz = bids[0] if bids else (1.0, 1.0)
    best_ask, ask_sz = asks[0] if asks else (1.0001, 1.0)
    mid = (best_bid + best_ask) / 2.0
    spread_bps = ((best_ask - best_bid) / mid) * 10_000
    imbalance = (bid_sz - ask_sz) / (bid_sz + ask_sz) if (bid_sz + ask_sz) > 0 else 0.0

    # Calculate returns over 3 prior windows strictly prior to cutoff
    closes = [p for ts, p in price_history if ts <= cutoff_ts]
    if not closes:
        closes = [mid]

    r1 = ((closes[-1] - closes[-2]) / closes[-2]) * 10_000 if len(closes) >= 2 else 0.0
    r2 = ((closes[-1] - closes[-6]) / closes[-6]) * 10_000 if len(closes) >= 6 else r1
    r3 = ((closes[-1] - closes[-16]) / closes[-16]) * 10_000 if len(closes) >= 16 else r2

    # Realized volatility (std dev of log returns in bps)
    log_rets = [math.log(closes[i] / closes[i-1]) for i in range(1, len(closes))] if len(closes) >= 2 else [0.0]
    mean_r = sum(log_rets) / len(log_rets)
    var_r = sum((x - mean_r) ** 2 for x in log_rets) / max(1, len(log_rets) - 1)
    r_vol = math.sqrt(var_r) * 10_000

    dd_bps = max(0.0, (peak_equity_usd - current_equity_usd) / peak_equity_usd) * 10_000 if peak_equity_usd > 0 else 0.0

    return MarketSnapshot(
        mid=mid,
        spread_bps=spread_bps,
        imbalance=imbalance,
        realized_vol_bps=r_vol,
        ret_w1_bps=r1,
        ret_w2_bps=r2,
        ret_w3_bps=r3,
        inventory_usd=inventory_usd,
        current_drawdown_bps=dd_bps,
        decision_cutoff_ts=cutoff_ts
    )
