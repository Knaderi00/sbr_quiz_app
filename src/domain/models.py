# src/domain/models.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union


Topic = Literal[
    "Ethics",
    "Income tax & NIC",
    "Capital gains",
    "Inheritance tax",
    "Loss reliefs",
    "Corporation tax",
    "Groups",
    "VAT",
]

Component = Literal[
    "definitions",
    "requirements",
    "exceptions",
    "proformas",
    "calculations",
    "filing_requirements",
    "penalties",
]

Priority = Literal["core", "niche", "edge"]

QuestionType = Literal["mcq_radio", "cloze_ab", "cloze_list", "proforma_drag"]


@dataclass(frozen=True)
class QuestionIndexRow:
    question_id: str
    topic: str
    component: str
    subtopic: str
    question_type: str
    difficulty: int
    priority: str
    active: str = "Y"
    tags: str = ""
    source_ref: str = ""
    version: int = 1


@dataclass(frozen=True)
class BaseQuestion:
    """
    Unified question object used by selection/scoring/UI.
    Concrete question types extend this with their payload.
    """
    question_id: str
    topic: str
    component: str
    subtopic: str
    question_type: str
    difficulty: int
    priority: str
    tags: str = ""
    source_ref: str = ""
    version: int = 1
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MCQRadioQuestion(BaseQuestion):
    prompt: str = ""
    options: List[str] = field(default_factory=list)  # ordered options for radio
    correct_option_index: int = 0  # index into options


@dataclass(frozen=True)
class ClozeABQuestion(BaseQuestion):
    prompt_template: str = ""
    gap_count: int = 1
    choice_a: str = ""
    choice_b: str = ""
    # e.g. ["A","B","A"] length == gap_count
    correct_by_gap: List[str] = field(default_factory=list)
    # e.g. [False, False, True]
    allow_repeat_by_gap: List[bool] = field(default_factory=list)


@dataclass(frozen=True)
class ClozeListQuestion(BaseQuestion):
    prompt_template: str = ""
    gap_count: int = 1
    # each gap has its own ordered list
    options_by_gap: List[List[str]] = field(default_factory=list)
    correct_by_gap: List[str] = field(default_factory=list)
    allow_repeat_by_gap: List[bool] = field(default_factory=list)
    enforce_unique_across_gaps: bool = True


@dataclass(frozen=True)
class ProformaDragQuestion(BaseQuestion):
    title: str = ""
    instructions: str = ""
    slot_count: int = 1
    # per slot, a label (what you show on the blank proforma)
    slot_labels: List[str] = field(default_factory=list)
    # per slot, the correct line_id
    slot_correct_line_ids: List[str] = field(default_factory=list)
    # draggable pool
    lines: List[Dict[str, Any]] = field(default_factory=list)  # each has line_id, text, is_distractor


Question = Union[MCQRadioQuestion, ClozeABQuestion, ClozeListQuestion, ProformaDragQuestion]


@dataclass(frozen=True)
class Attempt:
    attempt_id: str
    timestamp_utc: str
    session_id: str
    mode: Literal["quiz", "free_play"]
    quiz_id: str  # blank allowed for free_play
    topic: str
    component: str
    question_id: str
    question_type: str
    user_answer_raw: Any
    is_correct: bool
    exposure_index_in_session: int

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Convenience container type
QuestionBank = Dict[str, Question]
