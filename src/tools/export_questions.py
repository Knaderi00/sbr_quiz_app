from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
print(PROJECT_ROOT)


WORKBOOK = PROJECT_ROOT / "src" / "tools" / "atx_question_authoring_FIXED.xlsx"
OUT_DIR  = PROJECT_ROOT / "data" / "questions"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SHEETS = {
    "INDEX": "questions_index.csv",
    "MCQ": "questions_mcq_radio.csv",
    "CLOZE_AB": "questions_cloze_ab.csv",
    "CLOZE_LIST": "questions_cloze_list.csv",
    "PROFORMA": "questions_proforma_drag.csv",
}

def read_sheet(sheet: str) -> pd.DataFrame:
    df = pd.read_excel(WORKBOOK, sheet_name=sheet, dtype=str).fillna("")
    # standardise column names
    df.columns = [c.strip() for c in df.columns]
    if "question_id" in df.columns:
        df = df[df["question_id"].astype(str).str.strip() != ""]
    return df

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for sheet, fname in SHEETS.items():
        df = read_sheet(sheet)

        # Keep exact schema columns as in the sheet; no re-ordering here.
        out_path = OUT_DIR / fname
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"Wrote {len(df)} rows -> {out_path}")

if __name__ == "__main__":
    main()
