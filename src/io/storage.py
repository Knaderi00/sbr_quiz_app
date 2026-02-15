# src/io/storage.py
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.domain.models import Attempt


DEFAULT_USER_DATA_DIR = Path("user_data/attempts")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def attempts_path_for_month(base_dir: Path, yyyymm: str) -> Path:
    return base_dir / f"attempts_{yyyymm}.jsonl"


def append_attempt(path: Path, attempt: Attempt) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(attempt.to_dict(), ensure_ascii=False) + "\n")


def load_attempts(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for p in paths:
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def new_ids() -> Dict[str, str]:
    return {
        "attempt_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "quiz_id": str(uuid.uuid4()),
    }
