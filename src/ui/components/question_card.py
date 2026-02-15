from __future__ import annotations

from typing import Optional

import streamlit as st

from src.ui.lookups import Topic, Component
from src.ui.components.tube_map import render_tube_map


def _difficulty_pips(difficulty: int) -> str:
    difficulty = max(1, min(5, int(difficulty)))
    pips = []
    for i in range(1, 6):
        cls = "atx-pip on" if i <= difficulty else "atx-pip"
        pips.append(f"<span class='{cls}'></span>")
    return "<div class='atx-difficulty'>" + "".join(pips) + "</div>"


def render_question_card_shell(
    *,
    topic: Topic,
    component: Component,
    all_components: list[Component],
    subtopic: str,
    difficulty: int,
    priority_key: str,
    priority_label: str,
    prompt: str,
    source_ref: Optional[str] = None,
) -> None:
    # Header badges + pips
    left_bits = [
        f"<span class='atx-badge atx-badge-topic' style='--topic-color:{topic.color};'>{topic.label}</span>",
        f"<span class='atx-badge atx-badge-component' style='--component-color:{component.color};'>{component.label}</span>",
        f"<span class='atx-subtopic'>{subtopic}</span>",
    ]
    if source_ref:
        left_bits.append(f"<span class='atx-badge'>{source_ref}</span>")

    right_bits = [
        _difficulty_pips(difficulty),
        f"<span class='atx-badge atx-badge-priority {priority_key}'>{priority_label}</span>",
    ]

    st.markdown(
        f"""
<div class="atx-card" style="--topic-color:{topic.color};">
  <div class="atx-card-header">
    <div class="atx-card-header-left">
      {''.join(left_bits)}
    </div>
    <div style="display:flex; gap:10px; align-items:center;">
      {''.join(right_bits)}
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    # Tube map + prompt (outside the card div above; we render as standard Streamlit blocks to keep layouts stable)
    render_tube_map(all_components, active_component_key=component.key)
    st.markdown(f"<div class='atx-prompt'>{prompt}</div>", unsafe_allow_html=True)
