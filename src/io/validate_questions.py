# src/io/validate_questions.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import pandas as pd
import json

@dataclass(frozen=True)
class ValidationErrorDetail:
    message: str
    file: str = ""
    column: str = ""
    examples: List[str] = None


class QuestionsValidationError(Exception):
    def __init__(self, details: List[ValidationErrorDetail]):
        self.details = details
        super().__init__(self._format(details))

    @staticmethod
    def _format(details: List[ValidationErrorDetail]) -> str:
        def _ex_to_str(x) -> str:
            if isinstance(x, str):
                return x
            try:
                # nice for dict/list
                return json.dumps(x, ensure_ascii=False)
            except Exception:
                # fallback for anything else
                return repr(x)

        lines = []
        for d in details:
            prefix = f"- {d.message}"
            if getattr(d, "where", None):
                prefix += f" ({d.where})"
            lines.append(prefix)

            if d.examples:
                ex = "; ".join(_ex_to_str(x) for x in d.examples[:5])
                lines.append(f"    examples: {ex}")

        return "\n".join(lines)


def _require_columns(df: pd.DataFrame, required: List[str], file: str) -> List[ValidationErrorDetail]:
    missing = [c for c in required if c not in df.columns]
    if not missing:
        return []
    return [ValidationErrorDetail(message=f"Missing required columns: {missing}", file=file)]


def _no_blank(df: pd.DataFrame, col: str, file: str) -> Optional[ValidationErrorDetail]:
    if col not in df.columns:
        return None
    bad = df[df[col].astype(str).str.strip() == ""]
    if bad.empty:
        return None
    examples = bad.head(5).to_dict(orient="records")
    return ValidationErrorDetail(
        message=f"Blank values in required column",
        file=file,
        column=col,
        examples=[str(e) for e in examples],
    )


def validate_index(df_index: pd.DataFrame, file: str = "questions_index.csv") -> None:
    errors: List[ValidationErrorDetail] = []
    errors += _require_columns(
        df_index,
        required=[
            "question_id",
            "topic",
            "component",
            "subtopic",
            "question_type",
            "difficulty",
            "priority",
            "active",
        ],
        file=file,
    )

    for c in ["question_id", "topic", "component", "subtopic", "question_type", "priority", "active"]:
        err = _no_blank(df_index, c, file)
        if err:
            errors.append(err)

    if "question_id" in df_index.columns:
        dupes = df_index[df_index["question_id"].duplicated(keep=False)]
        if not dupes.empty:
            errors.append(
                ValidationErrorDetail(
                    message="Duplicate question_id values found",
                    file=file,
                    column="question_id",
                    examples=dupes["question_id"].head(10).astype(str).tolist(),
                )
            )

    if "difficulty" in df_index.columns:
        bad = df_index[~pd.to_numeric(df_index["difficulty"], errors="coerce").between(1, 5)]
        if not bad.empty:
            errors.append(
                ValidationErrorDetail(
                    message="difficulty must be an integer 1–5",
                    file=file,
                    column="difficulty",
                    examples=bad[["question_id", "difficulty"]].head(10).astype(str).to_dict(orient="records"),
                )
            )

    if errors:
        raise QuestionsValidationError(errors)


def validate_type_file(
    df_type: pd.DataFrame,
    file: str,
    required_cols: List[str],
    index_ids: Set[str],
) -> None:
    errors: List[ValidationErrorDetail] = []
    errors += _require_columns(df_type, required_cols, file=file)

    # FK check
    if "question_id" in df_type.columns:
        missing_fk = df_type[~df_type["question_id"].astype(str).isin(index_ids)]
        if not missing_fk.empty:
            errors.append(
                ValidationErrorDetail(
                    message="Type file contains question_id not present in index",
                    file=file,
                    column="question_id",
                    examples=missing_fk["question_id"].head(10).astype(str).tolist(),
                )
            )

    # required nonblank
    for c in required_cols:
        if c == "question_id":
            continue
        err = _no_blank(df_type, c, file)
        if err:
            errors.append(err)

    if errors:
        raise QuestionsValidationError(errors)


def validate_bank_coherence(
    df_index: pd.DataFrame,
    typed_ids_by_file: Dict[str, Set[str]],
) -> None:
    """
    Ensure every active index row has a corresponding row in exactly one type file.
    """
    errors: List[ValidationErrorDetail] = []
    index_active = df_index[df_index["active"].astype(str).str.upper().eq("Y")]
    index_ids = set(index_active["question_id"].astype(str).tolist())

    # union of typed IDs
    all_typed = set().union(*typed_ids_by_file.values()) if typed_ids_by_file else set()

    missing = sorted(list(index_ids - all_typed))
    if missing:
        errors.append(
            ValidationErrorDetail(
                message="Active questions in index missing from all type files",
                file="questions_index.csv",
                column="question_id",
                examples=missing[:10],
            )
        )

    # collisions: id appearing in more than one type file
    seen: Dict[str, List[str]] = {}
    for fname, ids in typed_ids_by_file.items():
        for qid in ids:
            seen.setdefault(qid, []).append(fname)
    collisions = {qid: files for qid, files in seen.items() if len(files) > 1}
    if collisions:
        ex = [f"{qid}: {files}" for qid, files in list(collisions.items())[:10]]
        errors.append(
            ValidationErrorDetail(
                message="question_id appears in multiple type files (must be exactly one)",
                examples=ex,
            )
        )

    if errors:
        raise QuestionsValidationError(errors)
