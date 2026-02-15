from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import streamlit as st


@dataclass(frozen=True)
class ClozeListGap:
    label: str
    options: List[str]


@dataclass(frozen=True)
class ClozeListSpec:
    """
    - prompt_template uses {gap1}, {gap2}, ... placeholders.
    - gaps are ordered and each has its own option list.
    """
    prompt_template: str
    gaps: List[ClozeListGap]
    enforce_unique_across_gaps: bool = True  # UI hint only; scoring enforces rules.


def _gap_key(question_id: str, gap_index: int) -> str:
    return f"cloze_list::{question_id}::gap{gap_index}"


def render_cloze_list(
    *,
    question_id: str,
    spec: ClozeListSpec,
    # current_values: map gap_index -> selected string (1-indexed)
    current_values: Optional[Dict[int, str]] = None,
    disabled: bool = False,
) -> Tuple[str, Dict[int, str]]:
    """
    Returns:
      rendered_prompt (string with chosen values inserted)
      selections: dict gap_index -> selected string
    """
    current_values = current_values or {}
    selections: Dict[int, str] = {}

    # Optionally prevent duplicates in UI (soft prevention; users can still pick duplicates
    # if options overlap—this just helps).
    used_values: set[str] = set()

    for i, gap in enumerate(spec.gaps, start=1):
        opts = list(gap.options)

        # Soft uniqueness: remove used options from later gaps if enforce_unique_across_gaps
        if spec.enforce_unique_across_gaps:
            opts = [o for o in opts if o not in used_values]

        # Default selection
        default = current_values.get(i)
        if default not in opts:
            default = opts[0] if opts else ""

        picked = st.selectbox(
            gap.label or f"Gap {i}",
            options=opts if opts else [""],
            index=(opts.index(default) if default in opts and opts else 0),
            key=_gap_key(question_id, i),
            disabled=disabled,
        )

        selections[i] = picked
        if picked:
            used_values.add(picked)

    rendered = spec.prompt_template
    for i in range(1, len(spec.gaps) + 1):
        rendered = rendered.replace(f"{{gap{i}}}", selections.get(i, ""))

    st.markdown(rendered)

    return rendered, selections
