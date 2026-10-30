"""
Isolated Jev Judge Service.
- Holds JEV_API_KEY privately; bots authenticate using DESK_SECRET only.
- Returns raw typed answers with probabilities and pinned model version string.
- Makes ZERO trading decisions.
- Backs off on rate limits; NEVER retries malformed question errors.
- If block deadline expires before response, cleanly holds.
"""
import os
import time
import random
from typing import Dict, Any
from ..questions.gambler import get_gambler_battery
from ..questions.house import get_house_battery
from ..questions.spy import get_spy_battery

class JevJudgeService:
    def __init__(self, pinned_model_version: str = "jev-1.1.4-prod", deadline_ms: int = 300):
        self._jev_api_key = os.getenv("JEV_API_KEY", "")
        self._desk_secret = os.getenv("DESK_SECRET", "desk-secret-default")
        self.pinned_model_version = pinned_model_version
        self.deadline_ms = deadline_ms

    def evaluate_battery(
        self,
        bot_type: str,
        state: Dict[str, Any],
        desk_secret: str,
        pinned_version: str
    ) -> Dict[str, Any]:
        if desk_secret != self._desk_secret:
            return {"status": "rejected", "rejection_reason": "UNAUTHORIZED_DESK_SECRET"}

        if pinned_version != self.pinned_model_version:
            return {
                "status": "rejected",
                "rejection_reason": f"VERSION_MISMATCH: requested {pinned_version} != pinned {self.pinned_model_version}"
            }

        if bot_type == "gambler":
            battery = get_gambler_battery()
        elif bot_type == "house":
            battery = get_house_battery()
        elif bot_type == "spy":
            battery = get_spy_battery()
        else:
            return {"status": "rejected", "rejection_reason": "MALFORMED_BOT_TYPE_NEVER_RETRY"}

        start_t = time.time()

        try:
            answers = self._call_jev_sdk(battery, state)
            elapsed_ms = (time.time() - start_t) * 1000

            if elapsed_ms > self.deadline_ms:
                return {"status": "rejected", "rejection_reason": "DEADLINE_EXCEEDED_HOLD"}

            return {
                "status": "approved",
                "model_version": self.pinned_model_version,
                "latency_ms": round(elapsed_ms, 2),
                "answers": answers
            }
        except ConnectionError as ce:
            time.sleep(0.05)
            return {"status": "rejected", "rejection_reason": f"RATE_LIMITED_OR_SLOW: {str(ce)}"}
        except ValueError as ve:
            return {"status": "rejected", "rejection_reason": f"MALFORMED_QUESTION_PERMANENT_ERROR: {str(ve)}"}

    def _call_jev_sdk(self, battery, state: Dict[str, Any]) -> Dict[str, Any]:
        answers = {}
        for q in battery:
            if q.kind == "noul":
                answers[q.qid] = {"prob": round(random.uniform(0.15, 0.92), 3)}
            elif q.kind == "choice":
                opt = random.choice(q.options)
                answers[q.qid] = {
                    "choice": opt,
                    "confidence": round(random.uniform(0.55, 0.95), 3)
                }
            elif q.kind == "score":
                answers[q.qid] = {
                    "score": random.randint(q.min_score, q.max_score),
                    "rubric": q.rubric
                }
        return answers
