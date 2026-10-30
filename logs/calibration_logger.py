"""
Structured Calibration Logger.
Records every snapshot, question battery, probability, and realized outcome.
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

class CalibrationLogger:
    def __init__(self, log_path: str = "trading_desk/logs/calibration.jsonl"):
        self.log_file = Path(log_path)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_decision_event(
        self,
        decision_id: str,
        bot_type: str,
        mode: str,
        snapshot: Dict[str, Any],
        answers: Dict[str, Any],
        policy_action: str,
        risk_veto: Optional[str],
        model_version: str,
        realized_outcome: Optional[int] = None
    ):
        record = {
            "decision_id": decision_id,
            "timestamp": int(time.time() * 1000),
            "bot_type": bot_type,
            "mode": mode,
            "model_version": model_version,
            "snapshot": snapshot,
            "answers": answers,
            "policy_action": policy_action,
            "risk_veto": risk_veto,
            "realized_outcome": realized_outcome
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
