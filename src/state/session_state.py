from __future__ import annotations

import uuid
import streamlit as st

def _new_uuid() -> str:
    return str(uuid.uuid4())


# Single source of truth for keys (avoid typos)
K = {
    # Identity
    "session_id": "session_id",

    # Sidebar selections
    "selected_topic": "selected_topic",
    "selected_mode": "selected_mode",              # "component_focus" | "full_sequence"
    "selected_subtopic": "selected_subtopic",      # optional filter across selected scope
    "selected_component": "selected_component",    # only if component_focus
    "run_kind": "run_kind",                        # "quiz" | "free_play"
    "quiz_size": "quiz_size",

    # Run lifecycle
    "run_id": "run_id",                            # changes per run
    "quiz_id": "quiz_id",                          # only for quiz
    "run_question_target": "run_question_target",  # quiz_size or None
    "run_completed": "run_completed",

    # Current question payload + exposure identity
    "current_q": "current_q",
    "current_exposure_id": "current_exposure_id",  # uuid per display

    # Per-question UI state (mirrors sample pattern)
    "selected_response": "selected_response",
    "answered": "answered",
    "is_correct": "is_correct",

    # Guard so submit only scores once per exposure
    "last_scored_exposure_id": "last_scored_exposure_id",

    # Counters
    "exposures_seen": "exposures_seen",  # counts displays (your requirement)
    "attempts_seen": "attempts_seen",    # counts submitted attempts (matches sample questions_seen)
    "score": "score",                    # correct attempts in current run

    # Attempt history buffer (append-only; persistence handled elsewhere)
    "attempts": "attempts",
}


def init_session_state() -> None:
    # Identity
    if K["session_id"] not in st.session_state:
        st.session_state[K["session_id"]] = _new_uuid()

    # Sidebar selections
    st.session_state.setdefault(K["selected_topic"], None)
    st.session_state.setdefault(K["selected_mode"], "component_focus")
    st.session_state.setdefault(K["selected_component"], None)
    st.session_state.setdefault(K["selected_subtopic"], None)   
    st.session_state.setdefault(K["run_kind"], "quiz")
    st.session_state.setdefault(K["quiz_size"], 10)

    # Run lifecycle
    st.session_state.setdefault(K["run_id"], _new_uuid())
    st.session_state.setdefault(K["quiz_id"], None)
    st.session_state.setdefault(K["run_question_target"], None)
    st.session_state.setdefault(K["run_completed"], False)

    # Current question + exposure
    st.session_state.setdefault(K["current_q"], None)
    st.session_state.setdefault(K["current_exposure_id"], None)

    # Per-question UI state
    st.session_state.setdefault(K["selected_response"], None)
    st.session_state.setdefault(K["answered"], False)
    st.session_state.setdefault(K["is_correct"], None)

    # Scoring guard
    st.session_state.setdefault(K["last_scored_exposure_id"], None)

    # Counters
    st.session_state.setdefault(K["exposures_seen"], 0)
    st.session_state.setdefault(K["attempts_seen"], 0)
    st.session_state.setdefault(K["score"], 0)

    # Attempt history
    st.session_state.setdefault(K["attempts"], [])
