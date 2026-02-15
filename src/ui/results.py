###
# A simple results panel that expects precomputed metrics (you’ll wire to analytics later). It’s designed to be called with a dict like:

# topic_stats = {
#   "vat": {"seen": 40, "correct": 28, "accuracy": 0.70},
#   ...
# }
###

from __future__ import annotations

from typing import Dict, Optional

import streamlit as st

from src.ui.lookups import Topic


def render_results_panel(
    *,
    topics_map: Dict[str, Topic],
    # topic_stats: topic_key -> {"seen": int, "correct": int, "accuracy": float}
    topic_stats: Dict[str, Dict[str, float]],
    title: str = "Performance",
    help_text: Optional[str] = None,
) -> None:
    st.subheader(title)
    if help_text:
        st.caption(help_text)

    # Summary tiles (overall)
    total_seen = sum(int(v.get("seen", 0)) for v in topic_stats.values())
    total_correct = sum(int(v.get("correct", 0)) for v in topic_stats.values())
    overall_acc = (total_correct / total_seen) if total_seen else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Seen", f"{total_seen}")
    c2.metric("Correct", f"{total_correct}")
    c3.metric("Accuracy", f"{overall_acc:.0%}")

    st.markdown("---")

    # Per-topic breakdown
    # Sort by lowest accuracy first (weak areas bubble up)
    items = []
    for k, v in topic_stats.items():
        acc = float(v.get("accuracy", 0.0))
        items.append((acc, k, v))
    items.sort(key=lambda x: x[0])

    for acc, topic_key, v in items:
        topic = topics_map.get(topic_key)
        label = topic.label if topic else topic_key
        seen = int(v.get("seen", 0))
        correct = int(v.get("correct", 0))
        colour = topic.color if topic else "#6B7280"

        st.markdown(
            f"""
<div style="display:flex; align-items:center; justify-content:space-between; padding:10px 12px; border-radius:12px; border:1px solid rgba(0,0,0,0.06); margin-bottom:8px;">
  <div style="display:flex; align-items:center; gap:10px;">
    <div style="width:12px; height:12px; border-radius:3px; background:{colour};"></div>
    <div style="font-weight:650;">{label}</div>
  </div>
  <div style="display:flex; gap:14px; color:rgba(0,0,0,0.70);">
    <div>Seen: <b>{seen}</b></div>
    <div>Correct: <b>{correct}</b></div>
    <div>Acc: <b>{acc:.0%}</b></div>
  </div>
</div>
            """,
            unsafe_allow_html=True,
        )
