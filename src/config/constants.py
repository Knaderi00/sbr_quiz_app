from __future__ import annotations

# ---- Widget keys (keep stable to preserve Streamlit state behaviour) ----
WKEY_MODE = "sidebar_mode"
WKEY_FLOW = "sidebar_flow"
WKEY_TOPIC = "sidebar_topic"
WKEY_COMPONENT = "sidebar_component"
WKEY_SUBTOPICS = "sidebar_subtopics"
WKEY_EMPHASIS = "sidebar_emphasis"

WKEY_ANSWER_RADIO = "answer_radio"

# ---- Modes / enums ----
MODE_QUIZ = "quiz_10"
MODE_FREE = "free_play"

FLOW_SEQUENCE = "sequence"
FLOW_FOCUS = "focus_component"

EMPHASIS_COVERAGE = "coverage"
EMPHASIS_BALANCED = "balanced"
EMPHASIS_WEAK = "weak_areas"

ALL_COMPONENT_KEYS_IN_ORDER = [
    "definitions",
    "requirements",
    "exceptions",
    "proformas",
    "calculations",
    "filing_requirements",
    "penalties",
]

ALL_TOPIC_KEYS = [
    "ethics",
    "income_tax_nic",
    "capital_gains",
    "inheritance_tax",
    "loss_reliefs",
    "corporation_tax",
    "groups",
    "vat",
]

ALL_PRIORITY_KEYS = ["core", "niche", "edge"]

# ---- Paths ----
LOOKUPS_TOPICS_PATH = "data/lookups/topics.json"
LOOKUPS_COMPONENTS_PATH = "data/lookups/components.json"
LOOKUPS_PRIORITIES_PATH = "data/lookups/priorities.json"
