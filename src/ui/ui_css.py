from __future__ import annotations

import streamlit as st

def apply_global_css() -> None:
    st.markdown(
        """
<style>
/* ---- Card ---- */
.atx-card {
  border-radius: 16px;
  padding: 18px 18px 14px 18px;
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(0,0,0,0.06);
  border-left: 10px solid var(--topic-color, #6B7280);
  margin-bottom: 14px;
}
.atx-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.atx-card-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.atx-subtopic {
  font-size: 0.92rem;
  color: rgba(0,0,0,0.65);
}

/* ---- Badges ---- */
.atx-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 600;
  line-height: 1.2;
  border: 1px solid rgba(0,0,0,0.08);
}
.atx-badge-topic {
  background: var(--topic-color, #6B7280);
  color: #ffffff;
  border: 1px solid rgba(255,255,255,0.18);
}
.atx-badge-component {
  background: var(--component-color, #0EA5E9);
  color: #ffffff;
  border: 1px solid rgba(255,255,255,0.18);
}
.atx-badge-priority {
  background: rgba(0,0,0,0.04);
  color: rgba(0,0,0,0.75);
}
.atx-badge-priority.core {
  background: rgba(16,185,129,0.15);
  color: #065F46;
  border-color: rgba(16,185,129,0.35);
}
.atx-badge-priority.niche {
  background: rgba(245,158,11,0.15);
  color: #7C2D12;
  border-color: rgba(245,158,11,0.35);
}
.atx-badge-priority.edge {
  background: rgba(239,68,68,0.12);
  color: #7F1D1D;
  border-color: rgba(239,68,68,0.30);
}

/* ---- Difficulty pips ---- */
.atx-difficulty {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}
.atx-pip {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: rgba(0,0,0,0.15);
}
.atx-pip.on {
  background: rgba(0,0,0,0.65);
}

/* ---- Tube map ---- */
.atx-tube {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 10px 0 14px 0;
  flex-wrap: wrap;
}
.atx-stop {
  display: flex;
  align-items: center;
  gap: 6px;
}
.atx-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--dot-color, #0EA5E9);
  opacity: var(--dot-opacity, 0.35);
  transform: scale(var(--dot-scale, 1));
}
.atx-label {
  font-size: 0.78rem;
  color: rgba(0,0,0,0.62);
  opacity: var(--label-opacity, 0.55);
}
.atx-dot.active {
  opacity: 1;
  transform: scale(1.2);
}
.atx-label.active {
  opacity: 1;
  color: rgba(0,0,0,0.78);
  font-weight: 600;
}

/* ---- Prompt ---- */
.atx-prompt {
  font-size: 1.05rem;
  font-weight: 650;
  margin: 6px 0 10px 0;
}

/* ---- Context summary ---- */
.atx-context {
  font-size: 0.85rem;
  color: rgba(0,0,0,0.60);
  margin-top: 8px;
}
</style>
        """,
        unsafe_allow_html=True,
    )
