from __future__ import annotations

from typing import List, Optional

import streamlit as st

from src.config.constants import WKEY_ANSWER_RADIO


def render_mcq_radio(
    *,
    options: List[str],
    selected: Optional[str],
) -> str:
    # Keep selection stable by computing index, but avoid crashes if selected not in options.
    if selected is None or selected not in options:
        idx = 0
    else:
        idx = options.index(selected)

    choice = st.radio(
        "Select your answer:",
        options=options,
        index=idx,
        key=WKEY_ANSWER_RADIO,
    )
    return choice
