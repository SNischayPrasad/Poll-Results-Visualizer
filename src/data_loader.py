"""
data_loader.py
--------------
Loads poll data from a CSV file. Two layouts are supported:

1. LONG format (what this project generates): one row per answer, columns
   respondent_id, response_date, region, age_group, gender, question_id,
   question, selected_option.

2. WIDE format (a Google Forms / Microsoft Forms export): one row per
   respondent, one column per question, plus a 'Timestamp' column.
   It is converted ("melted") into the long format automatically.
"""

import pandas as pd

from src import config

# Common header names in form exports -> our standard column names
COLUMN_ALIASES = {
    "timestamp": "response_date", "date": "response_date", "submitted at": "response_date",
    "region": "region", "location": "region", "state": "region", "city": "region",
    "age group": "age_group", "age": "age_group", "age_group": "age_group",
    "gender": "gender", "sex": "gender",
    "respondent id": "respondent_id", "respondent_id": "respondent_id",
    "email address": "respondent_id",
}


def is_long_format(df):
    return {"question", "selected_option"}.issubset(df.columns)


def wide_to_long(df_wide):
    """Convert a Google-Form style wide export into the long format."""
    df = df_wide.rename(columns=lambda c: COLUMN_ALIASES.get(str(c).strip().lower(), c))

    if "respondent_id" not in df.columns:
        df.insert(0, "respondent_id", [f"R{i:05d}" for i in range(1, len(df) + 1)])
    for col in ["response_date", "region", "age_group", "gender"]:
        if col not in df.columns:
            df[col] = "Unknown"

    id_cols = ["respondent_id", "response_date", "region", "age_group", "gender"]
    question_cols = [c for c in df.columns if c not in id_cols]

    long_df = df.melt(id_vars=id_cols, value_vars=question_cols,
                      var_name="question", value_name="selected_option")

    # Re-use the IDs from config when the question text matches, else Q1, Q2...
    known = {q["text"]: qid for qid, q in config.QUESTIONS.items()}
    q_ids = {q: known.get(q, f"Q{i}") for i, q in enumerate(question_cols, start=1)}
    long_df["question_id"] = long_df["question"].map(q_ids)
    return long_df[config.LONG_COLUMNS]


def load_poll_data(path):
    """Read a CSV and always return it in long format."""
    df = pd.read_csv(path)
    if is_long_format(df):
        return df
    print(f"[loader] '{path}' looks like a wide form export -> converting to long format")
    return wide_to_long(df)
