# src/state/transitions.py
from __future__ import annotations

from datetime import datetime, timezone
import uuid
import streamlit as st

from .session_state import K


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_uuid() -> str:
    return str(uuid.uuid4())


# -----------------------------
# Core transition primitives
# -----------------------------

def reset_per_question_ui_state() -> None:
    """
    Mirrors your proven pattern:
    - new question must clear response + feedback flags
    """
    st.session_state[K["selected_response"]] = None
    st.session_state[K["answered"]] = False
    st.session_state[K["is_correct"]] = None
    # Important: clear last_scored_qid so the next submission can score
    st.session_state[K["last_scored_qid"]] = None


def set_current_question(q: dict) -> None:
    """
    Single source of truth for the currently displayed question.
    """
    st.session_state[K["current_q"]] = q
    reset_per_question_ui_state()


# -----------------------------
# Run lifecycle transitions
# -----------------------------

def start_new_run(run_kind: str, quiz_size: int | None = None) -> None:
    """
    Starting a new quiz/free-play run:
    - discard previous quiz score (UI-only requirement)
    - reset run counters
    - generate new run_id
    - assign quiz_id only for quiz
    """
    st.session_state[K["run_id"]] = _new_uuid()

    st.session_state[K["run_kind"]] = run_kind
    if run_kind == "quiz":
        st.session_state[K["quiz_id"]] = _new_uuid()
        st.session_state[K["run_question_target"]] = int(quiz_size or 10)
    else:
        st.session_state[K["quiz_id"]] = None
        st.session_state[K["run_question_target"]] = None

    st.session_state[K["run_questions_seen"]] = 0
    st.session_state[K["run_score"]] = 0
    st.session_state[K["run_completed"]] = False

    # Wipe current question (caller will ensure it is set)
    st.session_state[K["current_q"]] = None
    reset_per_question_ui_state()


# -----------------------------
# Selection (delegated hook)
# -----------------------------

def choose_next_question(select_fn, *, context: dict) -> dict:
    """
    select_fn: callable that returns the next question dict payload.
      It should implement your selection rules:
      unseen-first → lowest exposure → optional weak bias.

    context: contains anything selection needs (pool, stats, etc.)

    We keep this function tiny so state logic stays clean.
    """
    q = select_fn(context=context)
    if not isinstance(q, dict):
        raise ValueError("select_fn must return a dict question payload.")
    if "question_id" not in q:
        raise ValueError("Question payload must include 'question_id'.")
    if "question_type" not in q:
        raise ValueError("Question payload must include 'question_type'.")
    return q


def next_question(select_fn, *, context: dict) -> None:
    """
    Equivalent to your sample `new_question()`:
    - selects a question
    - sets it as current
    - resets per-question UI flags
    """
    q = choose_next_question(select_fn, context=context)
    set_current_question(q)

    # count exposure (every display counts)
    st.session_state[K["run_questions_seen"]] += 1
    st.session_state[K["global_exposures"]] += 1


# -----------------------------
# Answer submission
# -----------------------------

def submit_answer(score_fn, *, user_answer) -> None:
    """
    Equivalent to your sample `submit_answer()`:
    - no answer -> no-op
    - mark answered
    - score exactly once per question exposure
    - write an attempt record
    """
    q = st.session_state.get(K["current_q"])
    if q is None:
        return

    qid = q["question_id"]

    # No answer selected => do nothing
    if user_answer is None:
        return

    # If already scored this question exposure, do nothing (guards double clicks / reruns)
    if st.session_state.get(K["last_scored_qid"]) == qid and st.session_state.get(K["answered"]) is True:
        return

    st.session_state[K["selected_response"]] = user_answer
    st.session_state[K["answered"]] = True

    # Score using a type-aware function (per question type)
    is_corr = bool(score_fn(question=q, user_answer=user_answer))
    st.session_state[K["is_correct"]] = is_corr

    # Update run/global score exactly once
    st.session_state[K["last_scored_qid"]] = qid
    if is_corr:
        st.session_state[K["run_score"]] += 1
        st.session_state[K["global_correct"]] += 1

    # Attempt history (append-only)
    attempt = {
        "attempt_id": _new_uuid(),
        "timestamp_utc": _utc_now_iso(),
        "session_id": st.session_state[K["session_id"]],
        "run_id": st.session_state[K["run_id"]],
        "mode": st.session_state[K["run_kind"]],
        "quiz_id": st.session_state[K["quiz_id"]],
        "topic": q.get("topic"),
        "component": q.get("component"),
        "subtopic": q.get("subtopic"),
        "question_id": qid,
        "question_type": q.get("question_type"),
        "user_answer_raw": user_answer,
        "is_correct": is_corr,
        "exposure_index_in_run": st.session_state[K["run_questions_seen"]],
    }
    st.session_state[K["attempts"]].append(attempt)

    # Quiz completion check (UI-only: discard old quiz score when you start new run)
    target = st.session_state.get(K["run_question_target"])
    if st.session_state[K["run_kind"]] == "quiz" and isinstance(target, int):
        if st.session_state[K["run_questions_seen"]] >= target:
            st.session_state[K["run_completed"]] = True
