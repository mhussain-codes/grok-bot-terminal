"""
Book Manager:
1. Enforces exactly ONE open position at a time (no market scanning while open).
2. Maintains a bench for rejected candidates where the rejection reason sets bench duration.
"""
import time
from typing import Dict, Optional

class BookManager:
    def __init__(self):
        self.current_position: Optional[Dict] = None
        self.bench: Dict[str, float] = {}

        self.bench_durations = {
            "honeypot": 86400,
            "mint_authority": 86400,
            "low_liquidity": 1800,
            "wide_spread": 300,
            "exec_degraded": 600,
            "toxic_flow": 900,
            "default": 600
        }

    def has_open_position(self) -> bool:
        return self.current_position is not None

    def open_position(self, pos_details: Dict):
        if self.current_position is not None:
            raise RuntimeError("BOOK CONFLICT: Attempted to open position while another is active.")
        self.current_position = pos_details

    def close_position(self) -> Optional[Dict]:
        pos = self.current_position
        self.current_position = None
        return pos

    def bench_candidate(self, candidate_id: str, reason: str):
        now = time.time()
        duration = self.bench_durations["default"]
        for key, dur in self.bench_durations.items():
            if key in reason.lower():
                duration = dur
                break
        self.bench[candidate_id] = now + duration

    def is_benched(self, candidate_id: str) -> bool:
        unbench_at = self.bench.get(candidate_id, 0.0)
        return time.time() < unbench_at
