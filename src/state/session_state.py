# src/state/session_state.py
from __future__ import annotations

import uuid
from dataclasses import dataclass
import streamlit as st


# -----------------------------
# Canonical keys (avoid typos)
# -----------------------------

K = {
    # Session identity / run context
    "session_id": "session_id",
    "run_id": "run_id",  # changes when you start a new quiz/free-play run

    # User selections (sidebar)
    "selected_topic": "selected_topic",
    "selected_mode": "selected_mode",  # "component_focus" | "full_sequence"
    "selected_component": "selected_component",  # only if component_focus
    "run_kind": "run_kind",  # "quiz" | "free_play"
    "quiz_size": "quiz_size",

    # Run progress (per quiz/free-play run)
    "quiz_id": "quiz_id",  # only for quiz
    "run_question_target": "run_question_target",  # quiz_size or None
    "run_questions_seen": "run_questions_seen",  # exposures within current run
    "run_score": "run_score",
    "run_completed": "run_completed",

    # Current question (source of truth)
    "current_q": "current_q",  # dict payload from selection layer

    # Per-question UI state
    "selected_response": "selected_response",  # whatever UI captures
    "answered": "answered",
    "is_correct": "is_correct",

    # Guard against double counting
    "last_scored_qid": "last_scored_qid",  # question_id last scored

    # Global stats (across all runs in this Streamlit session)
    "global_exposures": "global_exposures",  # int
    "global_correct": "global_correct",      # int

    # Attempt history (in-memory buffer; you can persist elsewhere)
    "attempts": "attempts",  # list[dict]
}


def _new_uuid() -> str:
    return str(uuid.uuid4())


def init_session_state() -> None:
    """
    Idempotent initialiser.
    Must be safe to call on every rerun.
    """
    if K["session_id"] not in st.session_state:
        st.session_state[K["session_id"]] = _new_uuid()

    if K["run_id"] not in st.session_state:
        st.session_state[K["run_id"]] = _new_uuid()

    # Sidebar selections
    if K["selected_topic"] not in st.session_state:
        st.session_state[K["selected_topic"]] = None

    if K["selected_mode"] not in st.session_state:
        st.session_state[K["selected_mode"]] = "component_focus"

    if K["selected_component"] not in st.session_state:
        st.session_state[K["selected_component"]] = None

    if K["run_kind"] not in st.session_state:
        st.session_state[K["run_kind"]] = "quiz"

    if K["quiz_size"] not in st.session_state:
        st.session_state[K["quiz_size"]] = 10

    # Run progress
    if K["quiz_id"] not in st.session_state:
        st.session_state[K["quiz_id"]] = None

    if K["run_question_target"] not in st.session_state:
        st.session_state[K["run_question_target"]] = None

    if K["run_questions_seen"] not in st.session_state:
        st.session_state[K["run_questions_seen"]] = 0

    if K["run_score"] not in st.session_state:
        st.session_state[K["run_score"]] = 0

    if K["run_completed"] not in st.session_state:
        st.session_state[K["run_completed"]] = False

    # Current question + per-question UI state
    if K["current_q"] not in st.session_state:
        st.session_state[K["current_q"]] = None

    if K["selected_response"] not in st.session_state:
        st.session_state[K["selected_response"]] = None

    if K["answered"] not in st.session_state:
        st.session_state[K["answered"]] = False

    if K["is_correct"] not in st.session_state:
        st.session_state[K["is_correct"]] = None

    # Guards and global counters
    if K["last_scored_qid"] not in st.session_state:
        st.session_state[K["last_scored_qid"]] = None

    if K["global_exposures"] not in st.session_state:
        st.session_state[K["global_exposures"]] = 0

    if K["global_correct"] not in st.session_state:
        st.session_state[K["global_correct"]] = 0

    if K["attempts"] not in st.session_state:
        st.session_state[K["attempts"]] = []
