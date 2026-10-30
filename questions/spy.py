from typing import List
from .types import Question, ChoiceQuestion, NoulQuestion

def get_spy_battery() -> List[Question]:
    return [
        ChoiceQuestion(
            qid="spy_wallet_record",
            prompt="This wallet's record looks:",
            options=["skilled", "lucky", "bot-like", "insider-like", "other"]
        ),
        NoulQuestion(
            qid="spy_move_consistency",
            prompt="Is this move consistent with how this wallet usually trades?"
        ),
        ChoiceQuestion(
            qid="spy_mirror_decision",
            prompt="Mirror decision:",
            options=["full", "partial", "skip", "other"]
        ),
        NoulQuestion(
            qid="spy_rug_risk",
            prompt="Given the contract flags found, does this token look like a rug?"
        )
    ]
