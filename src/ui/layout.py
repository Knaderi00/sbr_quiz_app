from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import streamlit as st

from src.config.constants import (
    WKEY_MODE,
    WKEY_FLOW,
    WKEY_TOPIC,
    WKEY_COMPONENT,
    WKEY_SUBTOPICS,
    WKEY_EMPHASIS,
    MODE_QUIZ,
    MODE_FREE,
    FLOW_SEQUENCE,
    FLOW_FOCUS,
    EMPHASIS_COVERAGE,
    EMPHASIS_BALANCED,
    EMPHASIS_WEAK,
)
from src.ui.lookups import Topic, Component


@dataclass(frozen=True)
class SidebarSelection:
    mode: str
    flow: str
    topic_key: str
    focus_component_key: Optional[str]
    subtopics: List[str]
    emphasis: str


def _changed(prev: SidebarSelection | None, curr: SidebarSelection) -> bool:
    return prev != curr


def render_sidebar(
    *,
    topics: List[Topic],
    components: List[Component],
    available_subtopics: List[str],
    current_component_key: Optional[str],  # for sequence mode display only
    prev_selection: SidebarSelection | None,
) -> Tuple[SidebarSelection, bool]:
    st.sidebar.title("ATX Practice")

    # Mode
    mode_label = st.sidebar.radio(
        "Practice mode",
        options=[("10-question quiz", MODE_QUIZ), ("Free play", MODE_FREE)],
        format_func=lambda x: x[0],
        index=0,
        key=WKEY_MODE,
    )[1]

    # Flow
    flow_label = st.sidebar.radio(
        "Flow",
        options=[
            ("Work through components", FLOW_SEQUENCE),
            ("Focus on a single component", FLOW_FOCUS),
        ],
        format_func=lambda x: x[0],
        index=0,
        key=WKEY_FLOW,
    )[1]

    st.sidebar.markdown("---")

    # Topic selection (single)
    topic_labels = [t.label for t in topics]
    topic_by_label = {t.label: t for t in topics}
    chosen_label = st.sidebar.selectbox("Tax topic", options=topic_labels, key=WKEY_TOPIC)
    topic_key = topic_by_label[chosen_label].key

    # Component selection (conditional)
    focus_component_key: Optional[str] = None
    if flow_label == FLOW_FOCUS:
        comp_labels = [c.label for c in components]
        comp_by_label = {c.label: c for c in components}
        chosen_comp_label = st.sidebar.selectbox(
            "Component",
            options=comp_labels,
            key=WKEY_COMPONENT,
        )
        focus_component_key = comp_by_label[chosen_comp_label].key
    else:
        # Read-only display of the current component (orientation)
        if current_component_key:
            comp_map = {c.key: c for c in components}
            c = comp_map.get(current_component_key)
            if c:
                st.sidebar.caption(f"Current phase: **{c.label}**")

    # Subtopic filter (component-scoped)
    st.sidebar.markdown("---")
    subtopics = st.sidebar.multiselect(
        "Subtopics (current phase)",
        options=available_subtopics,
        default=available_subtopics,
        key=WKEY_SUBTOPICS,
    )

    # Emphasis
    st.sidebar.markdown("---")
    emphasis = st.sidebar.radio(
        "Training emphasis",
        options=[
            ("Coverage", EMPHASIS_COVERAGE),
            ("Balanced", EMPHASIS_BALANCED),
            ("Weak areas", EMPHASIS_WEAK),
        ],
        format_func=lambda x: x[0],
        index=0,
        key=WKEY_EMPHASIS,
    )[1]

    # Context summary
    st.sidebar.markdown("---")
    flow_txt = "Sequence" if flow_label == FLOW_SEQUENCE else "Focus"
    mode_txt = "Quiz" if mode_label == MODE_QUIZ else "Free play"
    st.sidebar.markdown(
        f"<div class='atx-context'>"
        f"<b>Context:</b> {mode_txt} • {flow_txt} • {chosen_label} • "
        f"Subtopics: {('All' if len(subtopics)==len(available_subtopics) else len(subtopics))}"
        f"</div>",
        unsafe_allow_html=True,
    )

    curr = SidebarSelection(
        mode=mode_label,
        flow=flow_label,
        topic_key=topic_key,
        focus_component_key=focus_component_key,
        subtopics=subtopics,
        emphasis=emphasis,
    )
    return curr, _changed(prev_selection, curr)
