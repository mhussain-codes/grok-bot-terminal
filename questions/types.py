from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class Question:
    qid: str
    prompt: str
    kind: str  # "noul", "choice", "score"

@dataclass(frozen=True)
class NoulQuestion(Question):
    def __init__(self, qid: str, prompt: str):
        super().__init__(qid=qid, prompt=prompt, kind="noul")

@dataclass(frozen=True)
class ChoiceQuestion(Question):
    options: List[str]
    def __init__(self, qid: str, prompt: str, options: List[str]):
        opts = list(options)
        if "other" not in opts:
            opts.append("other")
        super().__init__(qid=qid, prompt=prompt, kind="choice")
        object.__setattr__(self, "options", opts)

@dataclass(frozen=True)
class ScoreQuestion(Question):
    min_score: int
    max_score: int
    rubric: str
    def __init__(self, qid: str, prompt: str, min_score: int = 0, max_score: int = 3, rubric: str = ""):
        super().__init__(qid=qid, prompt=prompt, kind="score")
        object.__setattr__(self, "min_score", min_score)
        object.__setattr__(self, "max_score", max_score)
        object.__setattr__(self, "rubric", rubric)
