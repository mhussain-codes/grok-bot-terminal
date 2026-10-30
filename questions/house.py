from typing import List
from .types import Question, ChoiceQuestion, NoulQuestion, ScoreQuestion

def get_house_battery() -> List[Question]:
    return [
        ChoiceQuestion(
            qid="house_range_state",
            prompt="Range state:",
            options=["inside", "testing an edge", "breaking out", "other"]
        ),
        NoulQuestion(
            qid="house_toxic_flow",
            prompt="Is incoming flow toxic (informed traders picking you off)?"
        ),
        ScoreQuestion(
            qid="house_quote_environment",
            prompt="Is this an environment worth quoting into at all?",
            min_score=0, max_score=3, rubric="0=toxic/danger, 1=poor, 2=good, 3=ideal chop"
        ),
        NoulQuestion(
            qid="house_volume_active",
            prompt="Is volume still flowing through this market?"
        )
    ]
