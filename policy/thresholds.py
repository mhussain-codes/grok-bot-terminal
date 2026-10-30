"""
Policy layer: thresholds and combination weights in code.
One threshold per action, scaled to what being wrong costs.
"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class PolicyDecision:
    action: str              # "ENTER_LONG", "ENTER_SHORT", "QUOTE", "PULL_QUOTES", "MIRROR", "HOLD"
    confidence: float
    reason: str
    raw_scores: Dict[str, Any]

class DeskPolicy:
    def __init__(self):
        self.gambler_min_setup_score = 2.0
        self.gambler_min_action_confidence = 0.78
        self.gambler_max_exec_degraded_prob = 0.25
        self.gambler_min_buying_pressure = 0.65

        self.house_max_breakout_prob = 0.30
        self.house_max_toxic_flow_prob = 0.35
        self.house_min_quote_score = 2.0
        self.house_min_volume_prob = 0.60

        self.spy_min_skilled_prob = 0.75
        self.spy_min_consistency_prob = 0.70
        self.spy_max_rug_prob = 0.10

    def evaluate_gambler(self, answers: Dict[str, Any]) -> PolicyDecision:
        regime = answers.get("gambler_regime", {}).get("choice")
        action_choice = answers.get("gambler_action", {}).get("choice")
        action_prob = answers.get("gambler_action", {}).get("confidence", 0.0)
        setup_score = answers.get("gambler_setup_quality", {}).get("score", 0)
        exec_degraded = answers.get("gambler_exec_degraded", {}).get("prob", 1.0)
        buying_prob = answers.get("gambler_buying_pressure", {}).get("prob", 0.0)

        if exec_degraded > self.gambler_max_exec_degraded_prob:
            return PolicyDecision("HOLD", exec_degraded, "Execution degraded", answers)

        if regime == "trending" and setup_score >= self.gambler_min_setup_score:
            if action_choice == "long" and action_prob >= self.gambler_min_action_confidence and buying_prob >= self.gambler_min_buying_pressure:
                return PolicyDecision("ENTER_LONG", action_prob, "Trending setup with confirmed buying pressure", answers)
            elif action_choice == "short" and action_prob >= self.gambler_min_action_confidence:
                return PolicyDecision("ENTER_SHORT", action_prob, "Trending short setup", answers)

        return PolicyDecision("HOLD", action_prob, "Threshold not met or non-trending regime", answers)

    def evaluate_house(self, answers: Dict[str, Any]) -> PolicyDecision:
        range_state = answers.get("house_range_state", {}).get("choice")
        range_prob = answers.get("house_range_state", {}).get("confidence", 0.0)
        toxic_prob = answers.get("house_toxic_flow", {}).get("prob", 1.0)
        quote_score = answers.get("house_quote_environment", {}).get("score", 0)
        volume_prob = answers.get("house_volume_active", {}).get("prob", 0.0)

        if range_state == "breaking out" and range_prob >= self.house_max_breakout_prob:
            return PolicyDecision("PULL_QUOTES", range_prob, "Breakout detected: pausing grid", answers)
        if toxic_prob >= self.house_max_toxic_flow_prob:
            return PolicyDecision("PULL_QUOTES", toxic_prob, "Flow toxicity exceeds threshold", answers)
        if volume_prob < self.house_min_volume_prob:
            return PolicyDecision("HOLD", volume_prob, "Market volume dying", answers)
        if quote_score >= self.house_min_quote_score and range_state == "inside":
            return PolicyDecision("QUOTE", 1.0 - toxic_prob, "Optimal chop regime for grid quoting", answers)

        return PolicyDecision("HOLD", 0.0, "Suboptimal quoting environment", answers)

    def evaluate_spy(self, answers: Dict[str, Any]) -> PolicyDecision:
        wallet_record = answers.get("spy_wallet_record", {}).get("choice")
        skill_prob = answers.get("spy_wallet_record", {}).get("confidence", 0.0)
        consistency_prob = answers.get("spy_move_consistency", {}).get("prob", 0.0)
        mirror_choice = answers.get("spy_mirror_decision", {}).get("choice")
        rug_prob = answers.get("spy_rug_risk", {}).get("prob", 1.0)

        if rug_prob > self.spy_max_rug_prob:
            return PolicyDecision("HOLD", rug_prob, "Rug check failed", answers)
        if wallet_record == "skilled" and skill_prob >= self.spy_min_skilled_prob:
            if consistency_prob >= self.spy_min_consistency_prob and mirror_choice in ["full", "partial"]:
                return PolicyDecision("MIRROR", skill_prob, f"Mirror {mirror_choice}: skilled and consistent", answers)
        return PolicyDecision("HOLD", skill_prob, "Wallet criteria not met", answers)
