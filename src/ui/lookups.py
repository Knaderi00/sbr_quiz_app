from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

import streamlit as st

from src.config.constants import (
    LOOKUPS_TOPICS_PATH,
    LOOKUPS_COMPONENTS_PATH,
    LOOKUPS_PRIORITIES_PATH,
)


@dataclass(frozen=True)
class Topic:
    key: str
    label: str
    color: str


@dataclass(frozen=True)
class Component:
    key: str
    label: str
    abbr: str
    order: int
    color: str


@st.cache_data
def load_topics(path: str = LOOKUPS_TOPICS_PATH) -> List[Topic]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Topic(**t) for t in raw["topics"]]


@st.cache_data
def load_components(path: str = LOOKUPS_COMPONENTS_PATH) -> List[Component]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    comps = [Component(**c) for c in raw["components"]]
    return sorted(comps, key=lambda c: c.order)


@st.cache_data
def load_priorities(path: str = LOOKUPS_PRIORITIES_PATH) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {p["key"]: p["label"] for p in raw["priorities"]}


def topics_by_key(topics: List[Topic]) -> Dict[str, Topic]:
    return {t.key: t for t in topics}


def components_by_key(components: List[Component]) -> Dict[str, Component]:
    return {c.key: c for c in components}
