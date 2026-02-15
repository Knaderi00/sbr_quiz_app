from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import streamlit as st


@dataclass(frozen=True)
class ClozeABSpec:
    """
    UI spec for AB cloze:
    - prompt_template uses {gap1}, {gap2}, ... placeholders.
    - choice_a / choice_b are the two possible values per gap.
    - gap_count can be >= 1
    """
    prompt_template: str
    gap_count: int
    choice_a: str
    choice_b: str
    # Optional per-gap labels (e.g. "Residence test", "Tie count")
    gap_labels: Optional[List[str]] = None


def _gap_key(question_id: str, gap_index: int) -> str:
    # Keep widget keys stable and unique per question+gap
    return f"cloze_ab::{question_id}::gap{gap_index}"


def render_cloze_ab(
    *,
    question_id: str,
    spec: ClozeABSpec,
    # current_values: map gap_index -> "A" or "B" (1-indexed)
    current_values: Optional[Dict[int, str]] = None,
    disabled: bool = False,
) -> Tuple[str, Dict[int, str]]:
    """
    Returns:
      rendered_prompt (string with chosen values inserted)
      selections: dict gap_index -> "A"|"B"
    """
    current_values = current_values or {}
    selections: Dict[int, str] = {}

    # Build UI controls for each gap
    for i in range(1, spec.gap_count + 1):
        label = None
        if spec.gap_labels and len(spec.gap_labels) >= i:
            label = spec.gap_labels[i - 1]
        label = label or f"Gap {i}"

        default = current_values.get(i, "A")
        idx = 0 if default == "A" else 1

        picked = st.radio(
            label,
            options=["A", "B"],
            index=idx,
            horizontal=True,
            key=_gap_key(question_id, i),
            disabled=disabled,
        )
        selections[i] = picked

    # Render the prompt with selected values substituted
    rendered = spec.prompt_template
    for i in range(1, spec.gap_count + 1):
        chosen = selections.get(i, "A")
        chosen_text = spec.choice_a if chosen == "A" else spec.choice_b
        rendered = rendered.replace(f"{{gap{i}}}", chosen_text)

    # Show the rendered prompt as a nice block (optional)
    st.markdown(rendered)

    return rendered, selections
