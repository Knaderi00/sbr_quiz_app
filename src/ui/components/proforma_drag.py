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

    # Store order in session_state via key; Streamlit will persist it
    # We display as a selectbox to pick a line, then up/down to reorder.
    if _pool_key(question_id) not in st.session_state:
        st.session_state[_pool_key(question_id)] = ordered_ids

    if current_order is not None:
        # If caller passes order, keep session_state aligned (e.g. when switching questions)
        st.session_state[_pool_key(question_id)] = ordered_ids

    pool_ids: List[str] = list(st.session_state[_pool_key(question_id)])

    # Pick a line to move
    display_options = [f"{idx}. {line_by_id[line_id].text}" for idx, line_id in enumerate(pool_ids, start=1)]
    picked_option = st.selectbox(
        "Select a line to move",
        options=display_options,
        index=0 if display_options else 0,
        disabled=disabled or not display_options,
        key=f"proforma_drag::{question_id}::picked_option",
    )
    picked_id = None
    if picked_option and display_options:
        picked_idx = display_options.index(picked_option)
        picked_id = pool_ids[picked_idx]

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

    # Faster movement for long proformas: move selected line directly to position N.
    st.markdown("**Move selected line to position**")
    current_pos = 1
    if picked_id is not None and picked_id in pool_ids:
        current_pos = pool_ids.index(picked_id) + 1

    # Keep controls grouped on the left and aligned to the input baseline.
    move_col1, move_col2, move_col3, move_col4, _spacer = st.columns([2.8, 1.3, 1.3, 1.3, 8.6], gap="small")
    with move_col1:
        target_pos = st.number_input(
            "Target position",
            min_value=1,
            max_value=max(1, len(pool_ids)),
            value=current_pos,
            step=1,
            disabled=disabled or picked_id is None or not pool_ids,
            key=f"proforma_drag::{question_id}::target_pos",
            help="Enter the row number to move the selected line to.",
        )

    def _align_button_row() -> None:
        # Nudge button columns down so buttons align with the number input control row.
        st.markdown("<div style='height: 1.9rem;'></div>", unsafe_allow_html=True)

    with move_col2:
        _align_button_row()
        move_to_position = st.button(
            "Move",
            disabled=disabled or picked_id is None or not pool_ids,
            key=f"proforma_drag::{question_id}::move_to_position",
        )
    with move_col3:
        _align_button_row()
        move_to_top = st.button(
            "Top",
            disabled=disabled or picked_id is None or not pool_ids,
            key=f"proforma_drag::{question_id}::move_to_top",
        )
    with move_col4:
        _align_button_row()
        move_to_bottom = st.button(
            "Bottom",
            disabled=disabled or picked_id is None or not pool_ids,
            key=f"proforma_drag::{question_id}::move_to_bottom",
        )

    if picked_id is not None and (move_to_position or move_to_top or move_to_bottom):
        old_idx = pool_ids.index(picked_id)
        if move_to_top:
            new_idx = 0
        elif move_to_bottom:
            new_idx = len(pool_ids) - 1
        else:
            new_idx = max(0, min(len(pool_ids) - 1, int(target_pos) - 1))

        if new_idx != old_idx:
            moved = pool_ids.pop(old_idx)
            pool_ids.insert(new_idx, moved)
            st.session_state[_pool_key(question_id)] = pool_ids


    # Show ordered pool
    st.markdown("**Current order**")
    for i, lid in enumerate(st.session_state[_pool_key(question_id)], start=1):
        line = line_by_id[lid]
        st.markdown(f"{i}. {line.text}")

    ordered_pool = list(st.session_state[_pool_key(question_id)])
    selected = ordered_pool[: len(spec.slots)]

    st.markdown("---")
    st.markdown("**Your proforma (top lines mapped into slots)**")
    for idx, slot in enumerate(spec.slots, start=1):
        chosen_text = line_by_id[selected[idx - 1]].text if idx - 1 < len(selected) else ""
        st.markdown(f"- **{idx}. {slot.slot_label}** → {chosen_text}")

    return selected, ordered_pool
