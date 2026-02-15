from __future__ import annotations

from typing import Dict, List

from src.ui.lookups import (
    Topic,
    Component,
    load_topics,
    load_components,
    load_priorities,
    topics_by_key,
    components_by_key,
)
from src.ui.ui_css import apply_global_css


def init_ui() -> Dict[str, object]:
    """
    Call once in app.py.
    Returns a dict bundle with lookups and fast maps.
    """
    apply_global_css()

    topics: List[Topic] = load_topics()
    components: List[Component] = load_components()
    priorities: Dict[str, str] = load_priorities()

    return {
        "topics": topics,
        "components": components,
        "priorities": priorities,
        "topic_map": topics_by_key(topics),
        "component_map": components_by_key(components),
    }
