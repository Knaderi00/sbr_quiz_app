# src/domain/scoring.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.domain.models import (
    ClozeABQuestion,
    ClozeListQuestion,
    MCQRadioQuestion,
    ProformaDragQuestion,
    Question,
)


def score_attempt(question: Question, user_answer_raw: Any) -> Tuple[bool, Dict[str, Any]]:
    """
    Returns:
      (is_correct, details)

    details is a small structured dict you can log and/or render in UI.
    """
    if isinstance(question, MCQRadioQuestion):
        return _score_mcq(question, user_answer_raw)

    if isinstance(question, ClozeABQuestion):
        return _score_cloze_ab(question, user_answer_raw)

    if isinstance(question, ClozeListQuestion):
        return _score_cloze_list(question, user_answer_raw)

    if isinstance(question, ProformaDragQuestion):
        return _score_proforma_drag(question, user_answer_raw)

    return False, {"reason": "Unknown question type"}


def _score_mcq(q: MCQRadioQuestion, user_answer_raw: Any) -> Tuple[bool, Dict[str, Any]]:
    # UI can send either selected index or selected text; accept both
    selected_index = None
    selected_text = None

    if isinstance(user_answer_raw, int):
        selected_index = user_answer_raw
    elif isinstance(user_answer_raw, str):
        selected_text = user_answer_raw.strip()

    correct_text = q.options[q.correct_option_index] if q.options else ""
    is_correct = False

    if selected_index is not None:
        is_correct = (selected_index == q.correct_option_index)
    elif selected_text is not None:
        is_correct = (selected_text == correct_text)

    return is_correct, {
        "correct_option_index": q.correct_option_index,
        "correct_text": correct_text,
    }


def _score_cloze_ab(q: ClozeABQuestion, user_answer_raw: Any) -> Tuple[bool, Dict[str, Any]]:
    # expected: list like ["A","B",...] length gap_count
    answers: List[str] = []
    if isinstance(user_answer_raw, list):
        answers = [str(a).strip().upper() for a in user_answer_raw]
    elif isinstance(user_answer_raw, dict):
        # allow {"gap1":"A", "gap2":"B"}
        for i in range(1, q.gap_count + 1):
            answers.append(str(user_answer_raw.get(f"gap{i}", "")).strip().upper())

    answers = answers[: q.gap_count]
    while len(answers) < q.gap_count:
        answers.append("")

    per_gap = []
    ok = True
    for i in range(q.gap_count):
        corr = q.correct_by_gap[i] if i < len(q.correct_by_gap) else "A"
        got = answers[i]
        gap_ok = (got == corr)
        per_gap.append({"gap": i + 1, "got": got, "correct": corr, "ok": gap_ok})
        if not gap_ok:
            ok = False

    return ok, {"per_gap": per_gap, "choices": {"A": q.choice_a, "B": q.choice_b}}


def _score_cloze_list(q: ClozeListQuestion, user_answer_raw: Any) -> Tuple[bool, Dict[str, Any]]:
    # expected: list of chosen strings per gap, or dict {"gap1":"...", ...}
    answers: List[str] = []
    if isinstance(user_answer_raw, list):
        answers = [str(a).strip() for a in user_answer_raw]
    elif isinstance(user_answer_raw, dict):
        for i in range(1, q.gap_count + 1):
            answers.append(str(user_answer_raw.get(f"gap{i}", "")).strip())

    answers = answers[: q.gap_count]
    while len(answers) < q.gap_count:
        answers.append("")

    # enforce uniqueness if requested
    if q.enforce_unique_across_gaps:
        seen = set()
        for i, a in enumerate(answers):
            if not a:
                continue
            allow_repeat = q.allow_repeat_by_gap[i] if i < len(q.allow_repeat_by_gap) else False
            if (a in seen) and (not allow_repeat):
                return False, {"reason": "Duplicate choice across gaps not allowed", "answers": answers}
            seen.add(a)

    per_gap = []
    ok = True
    for i in range(q.gap_count):
        corr = q.correct_by_gap[i] if i < len(q.correct_by_gap) else ""
        got = answers[i]
        gap_ok = (got == corr)
        per_gap.append({"gap": i + 1, "got": got, "correct": corr, "ok": gap_ok})
        if not gap_ok:
            ok = False

    return ok, {"per_gap": per_gap, "options_by_gap": q.options_by_gap}


def _score_proforma_drag(q: ProformaDragQuestion, user_answer_raw: Any) -> Tuple[bool, Dict[str, Any]]:
    """
    Expected user_answer_raw: list of line_ids placed into slots in order
      e.g. ["L1","L3","L2"] length == slot_count
    Any mismatch => fail (no partial credit).
    """
    placed: List[str] = []
    if isinstance(user_answer_raw, list):
        placed = [str(x).strip() for x in user_answer_raw]
    elif isinstance(user_answer_raw, dict):
        # allow {"slot1":"L1","slot2":"L2",...}
        for i in range(1, q.slot_count + 1):
            placed.append(str(user_answer_raw.get(f"slot{i}", "")).strip())

    placed = placed[: q.slot_count]
    while len(placed) < q.slot_count:
        placed.append("")

    correct = q.slot_correct_line_ids[: q.slot_count]
    ok = (placed == correct)

    return ok, {
        "placed": placed,
        "correct": correct,
        "slot_labels": q.slot_labels,
    }
