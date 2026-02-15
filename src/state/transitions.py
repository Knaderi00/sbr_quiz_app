from __future__ import annotations

from datetime import datetime, timezone
import uuid
import streamlit as st
from .session_state import K


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# -----------------------------
# Core state resets (sample parity)
# -----------------------------

def _reset_per_question_ui_state() -> None:
    """
    EXACTLY mirrors your sample approach:
    - reset selection + feedback flags when a new question is shown
    """
    st.session_state[K["selected_response"]] = None
    st.session_state[K["answered"]] = False
    st.session_state[K["is_correct"]] = None
    st.session_state[K["last_scored_exposure_id"]] = None


def set_current_question(q: dict) -> None:
    """
    One place where we:
    - set the question payload
    - assign a new exposure_id (for guarding scoring + exposure counting)
    - reset per-question UI flags
    - increment exposures_seen ONCE per new display (requirement)
    """
    st.session_state[K["current_q"]] = q
    st.session_state[K["current_exposure_id"]] = _new_uuid()
    _reset_per_question_ui_state()

    # Exposure = question displayed (count each display)
    st.session_state[K["exposures_seen"]] += 1


# -----------------------------
# Run lifecycle (quiz vs free play)
# -----------------------------

def start_new_run(*, run_kind: str, quiz_size: int | None = None) -> None:
    """
    UI-only requirement: discard prior quiz score when new run starts.
    Attempt history is NOT deleted.
    """
    st.session_state[K["run_id"]] = _new_uuid()
    st.session_state[K["run_kind"]] = run_kind

    if run_kind == "quiz":
        st.session_state[K["quiz_id"]] = _new_uuid()
        st.session_state[K["run_question_target"]] = int(quiz_size or 10)
    else:
        st.session_state[K["quiz_id"]] = None
        st.session_state[K["run_question_target"]] = None

    st.session_state[K["run_completed"]] = False

    # Reset run scoring counters (matches your “new quiz discards old score”)
    st.session_state[K["attempts_seen"]] = 0
    st.session_state[K["score"]] = 0

    # Clear current question; caller will immediately set a new one
    st.session_state[K["current_q"]] = None
    st.session_state[K["current_exposure_id"]] = None
    _reset_per_question_ui_state()


# -----------------------------
# Next question selection hook
# -----------------------------

def next_question(select_fn, *, context: dict) -> None:
    """
    Equivalent to your sample `new_question()`:
    - pick a question (delegated)
    - set it as current (resets UI flags)
    """
    q = select_fn(context=context)
    if not isinstance(q, dict):
        raise ValueError("select_fn must return a dict payload.")
    if "question_id" not in q:
        raise ValueError("Question payload must include 'question_id'.")
    if "question_type" not in q:
        raise ValueError("Question payload must include 'question_type'.")
    set_current_question(q)


# -----------------------------
# Submit answer (sample parity + exposure guard)
# -----------------------------

def submit_answer(score_fn, *, user_answer) -> None:
    """
    Equivalent to your sample `submit_answer()`:
    - no answer -> return
    - mark answered
    - score exactly once per exposure_id (rerun / double click safe)
    - increment attempts_seen (matches sample questions_seen)
    - update score
    - append attempt record
    - mark quiz completed when attempts_seen reaches target
    """
    q = st.session_state.get(K["current_q"])
    exposure_id = st.session_state.get(K["current_exposure_id"])
    if q is None or exposure_id is None:
        return

    if user_answer is None:
        return

    # Already scored this exposure (guard)
    if st.session_state.get(K["last_scored_exposure_id"]) == exposure_id:
        return

    st.session_state[K["selected_response"]] = user_answer
    st.session_state[K["answered"]] = True

    is_corr = bool(score_fn(question=q, user_answer=user_answer))
    st.session_state[K["is_correct"]] = is_corr

    st.session_state[K["last_scored_exposure_id"]] = exposure_id

    # Attempt counters (sample parity)
    st.session_state[K["attempts_seen"]] += 1
    if is_corr:
        st.session_state[K["score"]] += 1

    # Attempt history (append-only)
    st.session_state[K["attempts"]].append(
        {
            "attempt_id": _new_uuid(),
            "timestamp_utc": _utc_now_iso(),
            "session_id": st.session_state[K["session_id"]],
            "run_id": st.session_state[K["run_id"]],
            "mode": st.session_state[K["run_kind"]],
            "quiz_id": st.session_state[K["quiz_id"]],
            "exposure_id": exposure_id,
            "question_id": q.get("question_id"),
            "question_type": q.get("question_type"),
            "topic": q.get("topic"),
            "component": q.get("component"),
            "subtopic": q.get("subtopic"),
            "user_answer_raw": user_answer,
            "is_correct": is_corr,
        }
    )

    # Quiz completion (based on attempts in this run)
    target = st.session_state.get(K["run_question_target"])
    if st.session_state[K["run_kind"]] == "quiz" and isinstance(target, int):
        if st.session_state[K["attempts_seen"]] >= target:
            st.session_state[K["run_completed"]] = True
