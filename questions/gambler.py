from typing import List
from .types import Question, ChoiceQuestion, NoulQuestion, ScoreQuestion

def get_gambler_battery() -> List[Question]:
    return [
        ChoiceQuestion(
            qid="gambler_regime",
            prompt="What regime is this market in?",
            options=["trending", "mean-reverting", "chaotic", "other"]
        ),
        NoulQuestion(
            qid="gambler_buying_pressure",
            prompt="Is buying pressure building right now?"
        ),
        ScoreQuestion(
            qid="gambler_setup_quality",
            prompt="How well does this match the setup in the rulebook?",
            min_score=0, max_score=3, rubric="0=invalid, 1=marginal, 2=clean, 3=textbook"
        ),
        ChoiceQuestion(
            qid="gambler_action",
            prompt="Best directional action:",
            options=["long", "short", "hold", "other"]
        ),
        NoulQuestion(
            qid="gambler_exec_degraded",
            prompt="Has execution quality degraded in the last minutes?"
        )
    ]
