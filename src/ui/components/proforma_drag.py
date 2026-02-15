from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import streamlit as st


@dataclass(frozen=True)
class ProformaSlot:
    """
    Represents one blank line in the proforma (a target slot).
    """
    slot_label: str  # e.g. "Less:", "Add back:", "Step 3:"


@dataclass(frozen=True)
class ProformaLine:
    """
    Represents one draggable line item (correct or distractor).
    """
    line_id: str
    text: str
    is_distractor: bool = False


@dataclass(frozen=True)
class ProformaDragSpec:
    title: str
    instructions: str
    slots: List[ProformaSlot]
    lines_pool: List[ProformaLine]  # correct + distractors


def _pool_key(question_id: str) -> str:
    return f"proforma_drag::{question_id}::pool_order"


def render_proforma_drag(
    *,
    question_id: str,
    spec: ProformaDragSpec,
    # current_order: list of line_ids representing current pool order
    current_order: Optional[List[str]] = None,
    disabled: bool = False,
) -> Tuple[List[str], List[str]]:
    """
    MVP interaction model:
    - Show the blank proforma slots (fixed count)
    - Show a reorderable pool list; user reorders so top N lines map to slot 1..N

    Returns:
      selected_line_ids: first len(slots) line_ids from the current ordered pool
      ordered_pool_line_ids: the full ordered pool line_ids
    """
    st.markdown(f"#### {spec.title}")
    if spec.instructions:
        st.caption(spec.instructions)

    # Build a stable pool order
    all_ids = [l.line_id for l in spec.lines_pool]
    if current_order:
        # Keep only known IDs, append missing at end
        ordered_ids = [i for i in current_order if i in all_ids] + [i for i in all_ids if i not in (current_order or [])]
    else:
        ordered_ids = all_ids

    line_by_id = {l.line_id: l for l in spec.lines_pool}

    # Blank proforma display (slots)
    st.markdown("**Blank proforma**")
    for idx, slot in enumerate(spec.slots, start=1):
        st.markdown(f"- **{idx}. {slot.slot_label}**  _(drop line here)_")

    st.markdown("---")
    st.markdown("**Lines pool (reorder; top lines fill the proforma)**")

    # Streamlit-native reorder UX: use multiselect + up/down buttons as MVP
    # This avoids external components but still allows "moving lines".
    # Selected list represents the current ordered pool.
    ordered_texts = [f"{line_by_id[i].text}" for i in ordered_ids]

    # Store order in session_state via key; Streamlit will persist it
    # We display as a selectbox to pick a line, then up/down to reorder.
    if _pool_key(question_id) not in st.session_state:
        st.session_state[_pool_key(question_id)] = ordered_ids

    if current_order is not None:
        # If caller passes order, keep session_state aligned (e.g. when switching questions)
        st.session_state[_pool_key(question_id)] = ordered_ids

    pool_ids: List[str] = list(st.session_state[_pool_key(question_id)])

    # Pick a line to move
    display_options = [line_by_id[i].text for i in pool_ids]
    picked_text = st.selectbox(
        "Select a line to move",
        options=display_options,
        index=0 if display_options else 0,
        disabled=disabled or not display_options,
        key=f"proforma_drag::{question_id}::picked_text",
    )
    picked_id = None
    for i in pool_ids:
        if line_by_id[i].text == picked_text:
            picked_id = i
            break

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        up = st.button("⬆ Up", disabled=disabled or picked_id is None, key=f"proforma_drag::{question_id}::up")
    with col2:
        down = st.button("⬇ Down", disabled=disabled or picked_id is None, key=f"proforma_drag::{question_id}::down")

    if picked_id is not None and (up or down):
        idx = pool_ids.index(picked_id)
        if up and idx > 0:
            pool_ids[idx - 1], pool_ids[idx] = pool_ids[idx], pool_ids[idx - 1]
        if down and idx < len(pool_ids) - 1:
            pool_ids[idx + 1], pool_ids[idx] = pool_ids[idx], pool_ids[idx + 1]
        st.session_state[_pool_key(question_id)] = pool_ids

    # Show ordered pool
    st.markdown("**Current order**")
    for i, lid in enumerate(st.session_state[_pool_key(question_id)], start=1):
        line = line_by_id[lid]
        tag = " (distractor)" if line.is_distractor else ""
        st.markdown(f"{i}. {line.text}{tag}")

    ordered_pool = list(st.session_state[_pool_key(question_id)])
    selected = ordered_pool[: len(spec.slots)]

    st.markdown("---")
    st.markdown("**Your proforma (top lines mapped into slots)**")
    for idx, slot in enumerate(spec.slots, start=1):
        chosen_text = line_by_id[selected[idx - 1]].text if idx - 1 < len(selected) else ""
        st.markdown(f"- **{idx}. {slot.slot_label}** → {chosen_text}")

    return selected, ordered_pool
