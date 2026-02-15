from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import random
from typing import Any, Dict, Optional

import streamlit as st

from src.state.session_state import init_session_state, K
from src.state.transitions import start_new_run, next_question, submit_answer

from src.io.load_questions import load_question_bank
from src.io.storage import (
    DEFAULT_USER_DATA_DIR,
    attempts_path_for_month,
    append_attempt,
    load_attempts,
)
from src.domain.selection import (
    filter_candidate_ids,
    compute_stats_from_attempt_rows,
    pick_next_question_id,
)
from src.domain.scoring import score_attempt

# UI components you uploaded / integrated
from src.ui.components.question_card import render_question_card_shell
from src.ui.components.mcq_radio import render_mcq_radio
from src.ui.components.cloze_ab import ClozeABSpec, render_cloze_ab
from src.ui.components.cloze_list import ClozeListSpec, ClozeListGap, render_cloze_list
from src.ui.components.proforma_drag import ProformaDragSpec, ProformaSlot, ProformaLine, render_proforma_drag
from src.ui.ui_css import apply_global_css

from src.ui.lookups import load_topics, load_components, load_priorities, topics_by_key, components_by_key

@st.cache_data(show_spinner=False)
def _ui_topics():
    topics = load_topics()
    return topics, topics_by_key(topics)

@st.cache_data(show_spinner=False)
def _ui_components():
    comps = load_components()
    return comps, components_by_key(comps)

@st.cache_data(show_spinner=False)
def _ui_priorities():
    return load_priorities()

# -----------------------------
# Config
# -----------------------------

DATA_DIR = Path("data/questions")
USER_ATTEMPTS_DIR = DEFAULT_USER_DATA_DIR

COMPONENT_SEQUENCE = [
    "definitions",
    "requirements",
    "exceptions",
    "proformas",
    "calculations",
    "filing_requirements",
    "penalties",
]

RUN_MODES = {
    "Component focus": "component_focus",
    "Full sequence": "full_sequence",
}

RUN_KINDS = {
    "10-question quiz": "quiz",
    "Free play": "free_play",
}

PRIORITY_LABELS = {
    "core": "Core",
    "niche": "Niche",
    "edge": "Edge-case",
}


# -----------------------------
# Caching / loading
# -----------------------------

@st.cache_data(show_spinner=False)
def _load_bank_cached(data_dir: str) -> dict:
    return load_question_bank(Path(data_dir))


@st.cache_data(show_spinner=False)
def _load_persisted_attempt_rows() -> list[dict]:
    p = USER_ATTEMPTS_DIR
    if not p.exists():
        return []
    paths = sorted(p.glob("attempts_*.jsonl"))
    return load_attempts(paths)


def _month_key_now_yyyymm() -> str:
    return datetime.utcnow().strftime("%Y%m")


# -----------------------------
# Lookups adapters (Topic/Component objects expected by card + tube map)
# -----------------------------

def _load_ui_lookups():
    """
    We try to use src.ui.lookups if present, but we only need objects
    with: topic.label, topic.color and component.key,label,abbr,color.

    render_question_card_shell() relies on these attributes.
    """
    try:
        import src.ui.lookups as L  # type: ignore
        return L
    except Exception:
        return None


_LOOKUPS = _load_ui_lookups()


def _fallback_topic(topic_label: str):
    # Minimal object with .label and .color (simple deterministic palette)
    class _T:
        def __init__(self, label: str, color: str):
            self.label = label
            self.color = color

    # Stable-ish colors by topic label hash (not pretty, but only used if lookups missing)
    palette = ["#3B82F6", "#22C55E", "#F97316", "#A855F7", "#EF4444", "#06B6D4", "#84CC16", "#EAB308"]
    color = palette[abs(hash(topic_label)) % len(palette)]
    return _T(topic_label, color)


def _fallback_component(component_key: str):
    class _C:
        def __init__(self, key: str, label: str, abbr: str, color: str):
            self.key = key
            self.label = label
            self.abbr = abbr
            self.color = color

    label = component_key.replace("_", " ").title()
    abbr = "".join([w[0] for w in label.split()])[:3].upper()
    palette = ["#111827", "#374151", "#6B7280", "#9CA3AF", "#4B5563", "#1F2937", "#52525B"]
    color = palette[COMPONENT_SEQUENCE.index(component_key) % len(palette)] if component_key in COMPONENT_SEQUENCE else "#374151"
    return _C(component_key, label, abbr, color)


def _get_topic_obj(topic_value: str):
    if _LOOKUPS is None:
        return _fallback_topic(topic_value)

    # common patterns: TOPICS list, TOPICS_BY_KEY dict
    for name in ("TOPICS", "topics"):
        items = getattr(_LOOKUPS, name, None)
        if isinstance(items, list):
            for t in items:
                if getattr(t, "key", None) == topic_value or getattr(t, "label", None) == topic_value:
                    return t

    for name in ("TOPICS_BY_KEY", "topics_by_key"):
        d = getattr(_LOOKUPS, name, None)
        if isinstance(d, dict):
            if topic_value in d:
                return d[topic_value]

    # last resort: maybe there is a function
    for fn in ("get_topic", "topic_by_key"):
        f = getattr(_LOOKUPS, fn, None)
        if callable(f):
            try:
                return f(topic_value)
            except Exception:
                pass

    return _fallback_topic(topic_value)


def _get_component_obj(component_key: str):
    if _LOOKUPS is None:
        return _fallback_component(component_key)

    for name in ("COMPONENTS", "components"):
        items = getattr(_LOOKUPS, name, None)
        if isinstance(items, list):
            for c in items:
                if getattr(c, "key", None) == component_key:
                    return c

    for name in ("COMPONENTS_BY_KEY", "components_by_key"):
        d = getattr(_LOOKUPS, name, None)
        if isinstance(d, dict):
            if component_key in d:
                return d[component_key]

    for fn in ("get_component", "component_by_key"):
        f = getattr(_LOOKUPS, fn, None)
        if callable(f):
            try:
                return f(component_key)
            except Exception:
                pass

    return _fallback_component(component_key)


def _all_component_objs_for_tube() -> list:
    return [_get_component_obj(k) for k in COMPONENT_SEQUENCE]


# -----------------------------
# Helpers: question payloads for transitions/UI
# -----------------------------

def _question_to_payload(q) -> dict:
    d = asdict(q)
    d["question_id"] = d.get("question_id")
    d["question_type"] = d.get("question_type")
    return d


def _ensure_sequence_state_keys() -> None:
    st.session_state.setdefault("sequence_component_index", 0)


def _available_components_for_topic(bank: dict, topic: str) -> list[str]:
    available = []
    for comp in COMPONENT_SEQUENCE:
        ids = filter_candidate_ids(bank, topic=topic, component=comp)
        if ids:
            available.append(comp)
    return available


def _current_component_for_run(bank: dict, topic: str, mode: str, component_focus: Optional[str]) -> Optional[str]:
    if not topic:
        return None

    if mode == "component_focus":
        return component_focus

    available = _available_components_for_topic(bank, topic)
    if not available:
        return None

    idx = int(st.session_state.get("sequence_component_index", 0))
    idx = max(0, min(idx, len(available) - 1))
    return available[idx]


def _select_question_payload(bank: dict, *, context: dict) -> dict:
    topic = context["topic"]
    mode = context["mode"]
    component_focus = context.get("component_focus")
    bias_weak = bool(context.get("bias_weak", False))

    comp = _current_component_for_run(bank, topic, mode, component_focus)
    if not comp:
        raise ValueError("No component available for selection.")

    candidate_ids = filter_candidate_ids(bank, topic=topic, component=comp)

    # full-sequence fallback: try subsequent non-empty components
    if not candidate_ids and mode == "full_sequence":
        available = _available_components_for_topic(bank, topic)
        idx = int(st.session_state.get("sequence_component_index", 0))
        for j in range(idx + 1, len(available)):
            st.session_state["sequence_component_index"] = j
            comp2 = available[j]
            candidate_ids = filter_candidate_ids(bank, topic=topic, component=comp2)
            if candidate_ids:
                comp = comp2
                break

    if not candidate_ids:
        raise ValueError("No questions found for selected topic/component.")

    persisted = _load_persisted_attempt_rows()
    in_session = st.session_state.get(K["attempts"], [])
    stats = compute_stats_from_attempt_rows([*persisted, *in_session])

    qid = pick_next_question_id(candidate_ids, stats, bias_weak_areas=bias_weak, rng=random.Random())
    payload = _question_to_payload(bank[qid])
    return payload


def _score_fn_factory(bank: dict):
    def _score_fn(*, question: dict, user_answer):
        qid = str(question.get("question_id", "")).strip()
        if not qid or qid not in bank:
            return False
        q_obj = bank[qid]
        is_correct, _details = score_attempt(q_obj, user_answer)
        return bool(is_correct)

    return _score_fn


def _attempt_dict_to_attempt(d: dict):
    from src.domain.models import Attempt

    return Attempt(
        attempt_id=str(d.get("attempt_id", "")),
        timestamp_utc=str(d.get("timestamp_utc", "")),
        session_id=str(d.get("session_id", "")),
        mode=str(d.get("mode", "quiz")),
        quiz_id=str(d.get("quiz_id", "")) if d.get("quiz_id") is not None else "",
        topic=str(d.get("topic", "")),
        component=str(d.get("component", "")),
        question_id=str(d.get("question_id", "")),
        question_type=str(d.get("question_type", "")),
        user_answer_raw=d.get("user_answer_raw"),
        is_correct=bool(d.get("is_correct", False)),
        exposure_index_in_session=int(st.session_state.get(K["exposures_seen"], 0)),
    )


def _persist_latest_attempt_if_any() -> None:
    attempts = st.session_state.get(K["attempts"], [])
    if not attempts:
        return

    latest = attempts[-1]
    latest_id = latest.get("attempt_id")
    if not latest_id:
        return

    guard_key = "last_persisted_attempt_id"
    if st.session_state.get(guard_key) == latest_id:
        return

    path = attempts_path_for_month(USER_ATTEMPTS_DIR, _month_key_now_yyyymm())
    append_attempt(path, _attempt_dict_to_attempt(latest))
    st.session_state[guard_key] = latest_id


# -----------------------------
# Rendering using your UI components
# -----------------------------

def _render_header_metrics():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Exposures (this run)", st.session_state[K["exposures_seen"]])
    with col2:
        st.metric("Attempts (this run)", st.session_state[K["attempts_seen"]])
    with col3:
        score = st.session_state[K["score"]]
        attempts = st.session_state[K["attempts_seen"]]
        acc = f"{(score / attempts * 100):.1f}%" if attempts else "—"
        st.metric("Accuracy (this run)", acc)


def _priority_label(priority_key: str) -> str:
    k = (priority_key or "").strip().lower()
    return PRIORITY_LABELS.get(k, priority_key or "")


def _render_question_using_components(q: dict) -> Any:
    # --- lookups (cached) ---
    topics_list, topics_map = _ui_topics()
    components_list, components_map = _ui_components()
    priorities = _ui_priorities()

    # --- resolve topic/component objects from question payload ---
    topic_val = str(q.get("topic", "")).strip()
    topic_obj = next((t for t in topics_list if t.label == topic_val), None) or topics_map.get(topic_val)
    if topic_obj is None:
        st.error(f"Unknown topic: {topic_val}")
        return None

    component_key = str(q.get("component", "")).strip()
    component_obj = components_map.get(component_key)
    if component_obj is None:
        st.error(f"Unknown component key: {component_key}")
        return None

    all_components = components_list  # for tube map

    # --- priority label ---
    priority_key = str(q.get("priority", "")).strip().lower()
    priority_label = priorities.get(priority_key, priority_key.title())

    # --- prompt text ---
    qtype = q.get("question_type")
    if qtype == "mcq_radio":
        prompt = str(q.get("prompt", "")).strip()
    elif qtype in ("cloze_ab", "cloze_list"):
        prompt = str(q.get("prompt_template", "")).strip()
    else:
        prompt = str(q.get("instructions", "")).strip() or str(q.get("title", "")).strip()

    # --- card shell ---
    render_question_card_shell(
        topic=topic_obj,
        component=component_obj,
        all_components=all_components,
        subtopic=str(q.get("subtopic", "")).strip(),
        difficulty=int(q.get("difficulty", 1)),
        priority_key=priority_key,
        priority_label=priority_label,
        prompt=prompt,
        source_ref=(str(q.get("source_ref", "")).strip() or None),
    )


    disabled = bool(st.session_state.get(K["answered"], False))

    # ---- MCQ radio ----
    if qtype == "mcq_radio":
        options = q.get("options", []) or []
        selected = st.session_state.get(K["selected_response"])
        choice = render_mcq_radio(options=options, selected=selected)
        st.session_state[K["selected_response"]] = choice
        return choice

    # ---- Cloze AB ----
    if qtype == "cloze_ab":
        spec = ClozeABSpec(
            prompt_template=str(q.get("prompt_template", "")).strip(),
            gap_count=int(q.get("gap_count", 1)),
            choice_a=str(q.get("choice_a", "")).strip(),
            choice_b=str(q.get("choice_b", "")).strip(),
            gap_labels=None,
        )

        current = st.session_state.get(K["selected_response"])
        # component expects dict[int,str]
        current_values: Dict[int, str] = {}
        if isinstance(current, dict):
            # allow either {"gap1":"A"} or {1:"A"}
            for k, v in current.items():
                try:
                    if isinstance(k, int):
                        current_values[k] = str(v).strip().upper()
                    else:
                        ks = str(k)
                        if ks.startswith("gap"):
                            current_values[int(ks.replace("gap", ""))] = str(v).strip().upper()
                except Exception:
                    continue

        _rendered, selections = render_cloze_ab(
            question_id=str(q.get("question_id")),
            spec=spec,
            current_values=current_values or None,
            disabled=disabled,
        )

        # Convert to scoring-friendly dict {"gap1":"A", ...}
        answer = {f"gap{i}": selections.get(i, "A") for i in range(1, spec.gap_count + 1)}
        st.session_state[K["selected_response"]] = answer
        return answer

    # ---- Cloze list ----
    if qtype == "cloze_list":
        gaps = []
        options_by_gap = q.get("options_by_gap", []) or []
        gap_count = int(q.get("gap_count", 1))
        for i in range(1, gap_count + 1):
            opts = options_by_gap[i - 1] if i - 1 < len(options_by_gap) else []
            gaps.append(ClozeListGap(label=f"Gap {i}", options=list(opts)))

        spec = ClozeListSpec(
            prompt_template=str(q.get("prompt_template", "")).strip(),
            gaps=gaps,
            enforce_unique_across_gaps=bool(q.get("enforce_unique_across_gaps", True)),
        )

        current = st.session_state.get(K["selected_response"])
        current_values: Dict[int, str] = {}
        if isinstance(current, dict):
            for k, v in current.items():
                try:
                    if isinstance(k, int):
                        current_values[k] = str(v).strip()
                    else:
                        ks = str(k)
                        if ks.startswith("gap"):
                            current_values[int(ks.replace("gap", ""))] = str(v).strip()
                except Exception:
                    continue

        _rendered, selections = render_cloze_list(
            question_id=str(q.get("question_id")),
            spec=spec,
            current_values=current_values or None,
            disabled=disabled,
        )

        answer = {f"gap{i}": selections.get(i, "") for i in range(1, len(spec.gaps) + 1)}
        st.session_state[K["selected_response"]] = answer
        return answer

    # ---- Proforma drag ----
    if qtype == "proforma_drag":
        # Build spec from payload produced by load_questions.py
        slots = [ProformaSlot(slot_label=s) for s in (q.get("slot_labels", []) or [])]
        lines = []
        for ln in (q.get("lines", []) or []):
            lines.append(
                ProformaLine(
                    line_id=str(ln.get("line_id", "")),
                    text=str(ln.get("text", "")),
                    is_distractor=bool(ln.get("is_distractor", False)),
                )
            )

        spec = ProformaDragSpec(
            title=str(q.get("title", "")).strip(),
            instructions=str(q.get("instructions", "")).strip(),
            slots=slots,
            lines_pool=lines,
        )

        # Optional: preserve pool order in selected_response (nice, but not required)
        current = st.session_state.get(K["selected_response"])
        current_order = None
        if isinstance(current, dict) and isinstance(current.get("ordered_pool"), list):
            current_order = [str(x) for x in current["ordered_pool"]]

        selected_line_ids, ordered_pool = render_proforma_drag(
            question_id=str(q.get("question_id")),
            spec=spec,
            current_order=current_order,
            disabled=disabled,
        )

        # Scoring expects list of line_ids for slots in order (no partial credit)
        # Keep ordered pool as extra state for continuity
        answer = {"slots": selected_line_ids, "ordered_pool": ordered_pool}
        st.session_state[K["selected_response"]] = answer
        return selected_line_ids

    st.warning(f"Unknown question_type: {qtype}")
    return None


# -----------------------------
# App
# -----------------------------

def main():
    st.set_page_config(page_title="ATX Drill App", layout="wide")
    apply_global_css() 
    init_session_state()
    _ensure_sequence_state_keys()

    bank = _load_bank_cached(str(DATA_DIR))

    # --- Sidebar ---
    st.sidebar.title("ATX Drill Settings")

    topics = sorted({q.topic for q in bank.values()})
    selected_topic = st.sidebar.selectbox(
        "Tax topic",
        options=["— Select —"] + topics,
        index=0
        if st.session_state[K["selected_topic"]] is None
        else (1 + topics.index(st.session_state[K["selected_topic"]]))
        if st.session_state[K["selected_topic"]] in topics
        else 0,
    )
    st.session_state[K["selected_topic"]] = None if selected_topic == "— Select —" else selected_topic

    selected_mode_label = st.sidebar.radio(
        "Mode",
        options=list(RUN_MODES.keys()),
        index=0 if st.session_state[K["selected_mode"]] == "component_focus" else 1,
    )
    st.session_state[K["selected_mode"]] = RUN_MODES[selected_mode_label]

    if st.session_state[K["selected_mode"]] == "component_focus" and st.session_state[K["selected_topic"]]:
        comps = _available_components_for_topic(bank, st.session_state[K["selected_topic"]])
        comp = st.sidebar.selectbox(
            "Component",
            options=["— Select —"] + comps,
            index=0
            if st.session_state[K["selected_component"]] is None
            else (1 + comps.index(st.session_state[K["selected_component"]]))
            if st.session_state[K["selected_component"]] in comps
            else 0,
        )
        st.session_state[K["selected_component"]] = None if comp == "— Select —" else comp
    else:
        st.session_state[K["selected_component"]] = None

    run_kind_label = st.sidebar.radio(
        "Run type",
        options=list(RUN_KINDS.keys()),
        index=0 if st.session_state[K["run_kind"]] == "quiz" else 1,
    )
    st.session_state[K["run_kind"]] = RUN_KINDS[run_kind_label]

    quiz_size = st.sidebar.slider("Quiz size", min_value=5, max_value=30, value=int(st.session_state[K["quiz_size"]]), step=5)
    st.session_state[K["quiz_size"]] = int(quiz_size)

    bias_weak = st.sidebar.checkbox("Bias weak areas (tiebreak)", value=False)

    st.sidebar.markdown("---")
    if st.sidebar.button("Start new run"):
        st.session_state["sequence_component_index"] = 0
        start_new_run(run_kind=st.session_state[K["run_kind"]], quiz_size=st.session_state[K["quiz_size"]])

    # --- Guard: need topic ---
    if not st.session_state[K["selected_topic"]]:
        st.title("ATX Drill App")
        st.info("Select a tax topic in the sidebar to begin.")
        return

    # --- Ensure we have a run + a question ---
    if st.session_state[K["current_q"]] is None and not st.session_state[K["run_completed"]]:
        if st.session_state[K["run_kind"]] == "quiz":
            start_new_run(run_kind="quiz", quiz_size=st.session_state[K["quiz_size"]])
        else:
            start_new_run(run_kind="free_play")

        st.session_state["sequence_component_index"] = 0

        ctx = {
            "topic": st.session_state[K["selected_topic"]],
            "mode": st.session_state[K["selected_mode"]],
            "component_focus": st.session_state[K["selected_component"]],
            "bias_weak": bias_weak,
        }
        next_question(lambda context: _select_question_payload(bank, context=context), context=ctx)

    # --- Main UI ---
    st.title("ATX Drill App")
    _render_header_metrics()
    st.markdown("---")

    if st.session_state[K["run_completed"]]:
        st.success(f"Quiz completed. Score: {st.session_state[K['score']]}/{st.session_state[K['attempts_seen']]}")
        if st.button("Start another quiz"):
            st.session_state["sequence_component_index"] = 0
            start_new_run(run_kind="quiz", quiz_size=st.session_state[K["quiz_size"]])
            ctx = {
                "topic": st.session_state[K["selected_topic"]],
                "mode": st.session_state[K["selected_mode"]],
                "component_focus": st.session_state[K["selected_component"]],
                "bias_weak": bias_weak,
            }
            next_question(lambda context: _select_question_payload(bank, context=context), context=ctx)
        return

    q = st.session_state[K["current_q"]]
    user_answer = _render_question_using_components(q)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("Check answer"):
            score_fn = _score_fn_factory(bank)

            # For proforma we pass the slots list (not the dict we keep in session)
            if isinstance(st.session_state.get(K["selected_response"]), dict) and q.get("question_type") == "proforma_drag":
                user_answer = (st.session_state[K["selected_response"]].get("slots") or user_answer)

            submit_answer(score_fn, user_answer=user_answer)
            _persist_latest_attempt_if_any()

    with col_b:
        if st.button("Next question"):
            ctx = {
                "topic": st.session_state[K["selected_topic"]],
                "mode": st.session_state[K["selected_mode"]],
                "component_focus": st.session_state[K["selected_component"]],
                "bias_weak": bias_weak,
            }
            next_question(lambda context: _select_question_payload(bank, context=context), context=ctx)

    # Feedback / solution
    if st.session_state[K["answered"]]:
        if st.session_state[K["is_correct"]]:
            st.success("✅ Correct")
        else:
            st.error("❌ Incorrect")

        exp = q.get("explanation", "")
        if exp:
            with st.expander("Explanation / marking guidance", expanded=True):
                st.write(exp)
    else:
        st.info("Complete the question and click **Check answer** to see if you're right.")


if __name__ == "__main__":
    main()
