# src/io/load_questions.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Set, Tuple

import pandas as pd

from src.domain.models import (
    ClozeABQuestion,
    ClozeListQuestion,
    MCQRadioQuestion,
    ProformaDragQuestion,
    Question,
    QuestionBank,
)
from src.io.validate_questions import (
    validate_bank_coherence,
    validate_index,
    validate_type_file,
)

DEFAULT_DATA_DIR = Path("data/questions")


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig").fillna("")


def load_question_bank(data_dir: Path = DEFAULT_DATA_DIR) -> QuestionBank:
    """
    Loads Option 2 files:
      - questions_index.csv
      - questions_mcq_radio.csv
      - questions_cloze_ab.csv
      - questions_cloze_list.csv
      - questions_proforma_drag.csv

    Returns:
      Dict[question_id, Question]
    """
    data_dir = Path(data_dir)

    index_path = data_dir / "questions_index.csv"
    df_index = _read_csv(index_path)
    validate_index(df_index, file=str(index_path))

    # active only
    df_index["active"] = df_index["active"].astype(str).str.upper()
    df_index_active = df_index[df_index["active"].eq("Y")].copy()
    index_ids: Set[str] = set(df_index_active["question_id"].astype(str).tolist())

    # Load type files (if present)
    typed: Dict[str, pd.DataFrame] = {}
    typed_ids: Dict[str, Set[str]] = {}

    def load_typed(fname: str) -> Tuple[pd.DataFrame, Set[str]]:
        p = data_dir / fname
        if not p.exists():
            return pd.DataFrame(), set()
        df = _read_csv(p)
        ids = set(df["question_id"].astype(str).tolist()) if "question_id" in df.columns else set()
        return df, ids

    df_mcq, ids_mcq = load_typed("questions_mcq_radio.csv")
    if not df_mcq.empty:
        validate_type_file(
            df_mcq,
            file=str(data_dir / "questions_mcq_radio.csv"),
            required_cols=["question_id", "prompt", "correct_option"],
            index_ids=index_ids,
        )
        typed["mcq_radio"] = df_mcq
        typed_ids["questions_mcq_radio.csv"] = ids_mcq

    df_ab, ids_ab = load_typed("questions_cloze_ab.csv")
    if not df_ab.empty:
        validate_type_file(
            df_ab,
            file=str(data_dir / "questions_cloze_ab.csv"),
            required_cols=["question_id", "prompt_template", "gap_count", "choice_a", "choice_b"],
            index_ids=index_ids,
        )
        typed["cloze_ab"] = df_ab
        typed_ids["questions_cloze_ab.csv"] = ids_ab

    df_list, ids_list = load_typed("questions_cloze_list.csv")
    if not df_list.empty:
        validate_type_file(
            df_list,
            file=str(data_dir / "questions_cloze_list.csv"),
            required_cols=["question_id", "prompt_template", "gap_count", "enforce_unique_across_gaps"],
            index_ids=index_ids,
        )
        typed["cloze_list"] = df_list
        typed_ids["questions_cloze_list.csv"] = ids_list

    df_pf, ids_pf = load_typed("questions_proforma_drag.csv")
    if not df_pf.empty:
        validate_type_file(
            df_pf,
            file=str(data_dir / "questions_proforma_drag.csv"),
            required_cols=["question_id", "title", "instructions", "slot_labels_json", "correct_line_ids_json", "lines_json"],
            index_ids=index_ids,
        )
        typed["proforma_drag"] = df_pf
        typed_ids["questions_proforma_drag.csv"] = ids_pf

    validate_bank_coherence(df_index_active, typed_ids_by_file=typed_ids)

    # Build a quick lookup from index metadata
    idx = df_index_active.set_index("question_id")

    bank: QuestionBank = {}

    # ---- MCQ ----
    if "mcq_radio" in typed:
        df = typed["mcq_radio"].copy()
        for _, r in df.iterrows():
            qid = str(r["question_id"])
            if qid not in index_ids:
                continue
            meta = idx.loc[qid]

            # collect options a..e (and beyond if you add later)
            options = []
            for col in ["option_a", "option_b", "option_c", "option_d", "option_e", "option_f"]:
                if col in df.columns:
                    v = str(r.get(col, "")).strip()
                    if v:
                        options.append(v)

            # allow authoring as just prompt+correct_option if you prefer auto-generation later
            correct_letter = str(r["correct_option"]).strip().upper()
            letter_to_idx = {chr(ord("A") + i): i for i in range(len(options))}
            correct_idx = letter_to_idx.get(correct_letter, 0)

            bank[qid] = MCQRadioQuestion(
                question_id=qid,
                topic=str(meta["topic"]),
                component=str(meta["component"]),
                subtopic=str(meta["subtopic"]),
                question_type=str(meta["question_type"]),
                difficulty=int(meta["difficulty"]),
                priority=str(meta["priority"]),
                tags=str(meta.get("tags", "")),
                source_ref=str(meta.get("source_ref", "")),
                version=int(meta.get("version", 1)) if "version" in meta else 1,
                prompt=str(r.get("prompt", "")).strip(),
                options=options,
                correct_option_index=correct_idx,
                explanation=str(r.get("explanation", "")).strip(),
            )

    # ---- Cloze AB ----
    if "cloze_ab" in typed:
        df = typed["cloze_ab"].copy()
        for _, r in df.iterrows():
            qid = str(r["question_id"])
            if qid not in index_ids:
                continue
            meta = idx.loc[qid]
            gap_count = int(pd.to_numeric(r["gap_count"], errors="coerce") or 1)

            correct_by_gap = []
            allow_repeat = []
            for n in range(1, gap_count + 1):
                corr = str(r.get(f"gap{n}_correct", "")).strip().upper() or "A"
                correct_by_gap.append("A" if corr not in ("A", "B") else corr)
                ar = str(r.get(f"gap{n}_allow_repeat", "N")).strip().upper()
                allow_repeat.append(ar == "Y")

            bank[qid] = ClozeABQuestion(
                question_id=qid,
                topic=str(meta["topic"]),
                component=str(meta["component"]),
                subtopic=str(meta["subtopic"]),
                question_type=str(meta["question_type"]),
                difficulty=int(meta["difficulty"]),
                priority=str(meta["priority"]),
                tags=str(meta.get("tags", "")),
                source_ref=str(meta.get("source_ref", "")),
                version=int(meta.get("version", 1)) if "version" in meta else 1,
                prompt_template=str(r.get("prompt_template", "")).strip(),
                gap_count=gap_count,
                choice_a=str(r.get("choice_a", "")).strip(),
                choice_b=str(r.get("choice_b", "")).strip(),
                correct_by_gap=correct_by_gap,
                allow_repeat_by_gap=allow_repeat,
                explanation=str(r.get("explanation", "")).strip(),
            )

    # ---- Cloze List ----
    if "cloze_list" in typed:
        df = typed["cloze_list"].copy()

        def _parse_options_cell(raw: str) -> list[str]:
            s = (raw or "").strip()
            if not s:
                return []
            # Preferred: JSON array string e.g. ["1","2","3"]
            if s.startswith("[") and s.endswith("]"):
                try:
                    out = json.loads(s)
                    if isinstance(out, list):
                        return [str(x).strip() for x in out if str(x).strip()]
                except json.JSONDecodeError:
                    pass
            # Fallback: legacy pipe format e.g. "A|B|C"
            return [o.strip() for o in s.split("|") if o.strip()]
    
        for _, r in df.iterrows():
            qid = str(r["question_id"])
            if qid not in index_ids:
                continue
            meta = idx.loc[qid]
            gap_count = int(pd.to_numeric(r["gap_count"], errors="coerce") or 1)

            options_by_gap = []
            correct_by_gap = []
            allow_repeat = []
            for n in range(1, gap_count + 1):
                raw_opts = str(r.get(f"gap{n}_options", "")).strip()
                opts = _parse_options_cell(raw_opts)
                options_by_gap.append(opts)

                # keep correct as a string (and strip)
                corr = str(r.get(f"gap{n}_correct", "")).strip()
                correct_by_gap.append(corr)

                ar = str(r.get(f"gap{n}_allow_repeat", "N")).strip().upper()
                allow_repeat.append(ar == "Y")

            enforce_unique = str(r.get("enforce_unique_across_gaps", "Y")).strip().upper() == "Y"

            bank[qid] = ClozeListQuestion(
                question_id=qid,
                topic=str(meta["topic"]),
                component=str(meta["component"]),
                subtopic=str(meta["subtopic"]),
                question_type=str(meta["question_type"]),
                difficulty=int(meta["difficulty"]),
                priority=str(meta["priority"]),
                tags=str(meta.get("tags", "")),
                source_ref=str(meta.get("source_ref", "")),
                version=int(meta.get("version", 1)) if "version" in meta else 1,
                prompt_template=str(r.get("prompt_template", "")).strip(),
                gap_count=gap_count,
                options_by_gap=options_by_gap,
                correct_by_gap=correct_by_gap,
                allow_repeat_by_gap=allow_repeat,
                enforce_unique_across_gaps=enforce_unique,
                explanation=str(r.get("explanation", "")).strip(),
            )

    # ---- Proforma drag ----
    if "proforma_drag" in typed:
        df = typed["proforma_drag"].copy()
        for _, r in df.iterrows():
            qid = str(r["question_id"])
            if qid not in index_ids:
                continue
            meta = idx.loc[qid]

            # NEW: scalable slot labels + correct ids as JSON
            slot_labels_json = str(r.get("slot_labels_json", "")).strip()
            correct_ids_json = str(r.get("correct_line_ids_json", "")).strip()

            try:
                slot_labels = json.loads(slot_labels_json) if slot_labels_json else []
            except json.JSONDecodeError:
                slot_labels = []

            try:
                slot_correct_line_ids = json.loads(correct_ids_json) if correct_ids_json else []
            except json.JSONDecodeError:
                slot_correct_line_ids = []

            # slot_count derived (author doesn't need to maintain it)
            slot_count = len(slot_labels) if slot_labels else len(slot_correct_line_ids)
            slot_count = int(slot_count or 1)

            # Keep them aligned to slot_count
            slot_labels = [str(x).strip() for x in (slot_labels or [])][:slot_count]
            slot_correct_line_ids = [str(x).strip() for x in (slot_correct_line_ids or [])][:slot_count]

            # Existing: lines_json stays as-is
            lines_json = str(r.get("lines_json", "")).strip()
            try:
                lines = json.loads(lines_json) if lines_json else []
            except json.JSONDecodeError:
                lines = []

            bank[qid] = ProformaDragQuestion(
                question_id=qid,
                topic=str(meta["topic"]),
                component=str(meta["component"]),
                subtopic=str(meta["subtopic"]),
                question_type=str(meta["question_type"]),
                difficulty=int(meta["difficulty"]),
                priority=str(meta["priority"]),
                tags=str(meta.get("tags", "")),
                source_ref=str(meta.get("source_ref", "")),
                version=int(meta.get("version", 1)) if "version" in meta else 1,
                title=str(r.get("title", "")).strip(),
                instructions=str(r.get("instructions", "")).strip(),
                slot_count=slot_count,
                slot_labels=slot_labels,
                slot_correct_line_ids=slot_correct_line_ids,
                lines=lines,
                explanation=str(r.get("explanation", "")).strip(),
            )


    return bank
