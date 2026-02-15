# src/domain/selection.py
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from src.domain.models import Question, QuestionBank


@dataclass(frozen=True)
class QuestionStats:
    exposures: int
    attempts: int
    correct: int

    @property
    def accuracy(self) -> float:
        return (self.correct / self.attempts) if self.attempts > 0 else 0.0


def compute_stats_from_attempt_rows(attempt_rows: Iterable[Dict]) -> Dict[str, QuestionStats]:
    """
    attempt_rows are dicts loaded from JSONL.
    We treat each attempt row as an exposure.
    """
    agg: Dict[str, Dict[str, int]] = {}
    for r in attempt_rows:
        qid = str(r.get("question_id", "")).strip()
        if not qid:
            continue
        agg.setdefault(qid, {"exposures": 0, "attempts": 0, "correct": 0})
        agg[qid]["exposures"] += 1
        agg[qid]["attempts"] += 1
        if bool(r.get("is_correct", False)):
            agg[qid]["correct"] += 1

    out: Dict[str, QuestionStats] = {}
    for qid, a in agg.items():
        out[qid] = QuestionStats(exposures=a["exposures"], attempts=a["attempts"], correct=a["correct"])
    return out


def pick_next_question_id(
    candidate_ids: List[str],
    stats: Dict[str, QuestionStats],
    bias_weak_areas: bool = False,
    rng: Optional[random.Random] = None,
) -> str:
    """
    Priority:
      1) unseen first (exposures == 0)
      2) lowest exposures
      3) optionally bias weak (lower accuracy) as tiebreak
      4) random final tiebreak
    """
    rng = rng or random.Random()

    def exposures(qid: str) -> int:
        return stats.get(qid, QuestionStats(0, 0, 0)).exposures

    def accuracy(qid: str) -> float:
        return stats.get(qid, QuestionStats(0, 0, 0)).accuracy

    unseen = [qid for qid in candidate_ids if exposures(qid) == 0]
    pool = unseen if unseen else candidate_ids[:]

    # sort by exposures asc
    pool.sort(key=lambda qid: exposures(qid))

    # take minimal exposure group
    min_exp = exposures(pool[0]) if pool else 0
    min_group = [qid for qid in pool if exposures(qid) == min_exp]

    if bias_weak_areas and len(min_group) > 1:
        # bias to weakest accuracy among min exposure group
        min_group.sort(key=lambda qid: accuracy(qid))
        min_acc = accuracy(min_group[0])
        weakest = [qid for qid in min_group if abs(accuracy(qid) - min_acc) < 1e-9]
        return rng.choice(weakest)

    return rng.choice(min_group)


def filter_candidate_ids(
    bank: QuestionBank,
    topic: Optional[str] = None,
    component: Optional[str] = None,
) -> List[str]:
    ids: List[str] = []
    for qid, q in bank.items():
        if topic and q.topic != topic:
            continue
        if component and q.component != component:
            continue
        ids.append(qid)
    return ids
