"""
Hard veto risk engine checked before EVERY order.
NO MODEL CAN OVERRIDE THESE CHECKS.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass(frozen=True)
class RiskLimits:
    max_position_usd: float = 2500.0
    max_portfolio_exposure_usd: float = 5000.0
    daily_loss_limit_usd: float = 500.0
    max_leverage: float = 2.0
    range_lower_bound: float = 0.00001
    range_upper_bound: float = 100000.0
    min_edge_bps: float = 15.0
    estimated_fee_and_gas_bps: float = 7.0
    pinned_model_version: str = "jev-1.1.4-prod"

class RiskEngine:
    def __init__(self, limits: Optional[RiskLimits] = None):
        self.limits = limits or RiskLimits()
        self.daily_realized_loss_usd: float = 0.0
        self.is_halted: bool = False
        self.halt_reason: Optional[str] = None

    def record_pnl(self, pnl_usd: float):
        if pnl_usd < 0:
            self.daily_realized_loss_usd += abs(pnl_usd)
            if self.daily_realized_loss_usd >= self.limits.daily_loss_limit_usd:
                self.is_halted = True
                self.halt_reason = (
                    f"DAILY LOSS LIMIT BREACHED: ${self.daily_realized_loss_usd:.2f} >= "
                    f"${self.limits.daily_loss_limit_usd:.2f}. Desk locked for human review."
                )

    def check_pre_order_veto(
        self,
        market: str,
        order_side: str,
        order_size_usd: float,
        current_position_usd: float,
        current_price: float,
        leverage: float,
        model_version_used: str,
        expected_edge_bps: float
    ) -> Tuple[bool, Optional[str]]:
        if self.is_halted:
            return False, f"VETO_DESK_HALTED: {self.halt_reason}"

        if model_version_used != self.limits.pinned_model_version:
            return False, (
                f"VETO_MODEL_VERSION_MISMATCH: Expected '{self.limits.pinned_model_version}', "
                f"got '{model_version_used}'. Refusing execution on unverified model."
            )

        new_pos_size = current_position_usd + order_size_usd
        if new_pos_size > self.limits.max_position_usd:
            return False, (
                f"VETO_MAX_POSITION: Size ${new_pos_size:.2f} exceeds cap of "
                f"${self.limits.max_position_usd:.2f}"
            )

        if leverage > self.limits.max_leverage:
            return False, (
                f"VETO_LEVERAGE_CAP: Leverage {leverage}x exceeds max allowed "
                f"{self.limits.max_leverage}x"
            )

        if current_price < self.limits.range_lower_bound or current_price > self.limits.range_upper_bound:
            return False, (
                f"VETO_RANGE_GUARD: Price {current_price} outside safe corridor "
                f"[{self.limits.range_lower_bound}, {self.limits.range_upper_bound}]"
            )

        total_friction_bps = self.limits.estimated_fee_and_gas_bps
        if expected_edge_bps <= total_friction_bps:
            return False, (
                f"VETO_NEGATIVE_EDGE: Expected edge {expected_edge_bps:.2f} bps <= "
                f"fees+gas {total_friction_bps:.2f} bps"
            )

        if self.daily_realized_loss_usd >= self.limits.daily_loss_limit_usd:
            self.is_halted = True
            self.halt_reason = "Daily loss threshold reached"
            return False, f"VETO_DAILY_LOSS: {self.halt_reason}"

        return True, None
