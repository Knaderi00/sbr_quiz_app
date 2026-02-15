from __future__ import annotations

import streamlit as st

from src.ui.lookups import Component


def render_tube_map(components: list[Component], active_component_key: str) -> None:
    parts: list[str] = ["<div class='atx-tube'>"]
    for c in components:
        is_active = c.key == active_component_key
        dot_class = "atx-dot active" if is_active else "atx-dot"
        label_class = "atx-label active" if is_active else "atx-label"
        dot_opacity = "1" if is_active else "0.35"
        label_opacity = "1" if is_active else "0.55"
        parts.append(
            f"<div class='atx-stop' style='--dot-color:{c.color}; --dot-opacity:{dot_opacity}; --label-opacity:{label_opacity}'>"
            f"<div class='{dot_class}' style='background:{c.color};'></div>"
            f"<div class='{label_class}'>{c.abbr}</div>"
            f"</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)
