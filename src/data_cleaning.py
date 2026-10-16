"""
data_cleaning.py
----------------
Turns a messy poll export into a clean, analysis-ready table and records
every change in a cleaning log (so the results are explainable/auditable).

Steps
1. Trim spaces and fix capitalisation in text columns.
2. Standardise region names ("NORTH", " north " -> "North").
3. Match answers to the official option list (case-insensitive).
4. Remove blank and invalid answers.
5. Remove duplicate submissions (same respondent + same question).
6. Fill missing demographics with "Unknown" (keeps the vote, flags the gap).
7. Parse dates into real datetime values.
"""

import pandas as pd

from src import config

INVALID_VALUES = {"", "n/a", "na", "-", "???", "none", "null", "nan"}


def _clean_text(series):
    return series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)


def clean_poll_data(df, verbose=True):
    """Return (clean_df, cleaning_log)."""
    log = {"rows_in": len(df)}
    df = df.copy()

    # 1) Tidy text columns
    for col in ["respondent_id", "region", "age_group", "gender", "question_id",
                "question", "selected_option"]:
        df[col] = _clean_text(df[col])

    # 2) Standardise categories with title case ("north" -> "North")
    df["region"] = df["region"].str.title()
    df["gender"] = df["gender"].str.title()

    # 3) Map answers to the official spelling (only for questions we know)
    def canonical(row):
        ans = row["selected_option"]
        q = config.QUESTIONS.get(row["question_id"])
        if pd.isna(ans) or q is None:
            return ans
        lookup = {opt.lower(): opt for opt in q["options"]}
        return lookup.get(str(ans).lower(), ans)

    df["selected_option"] = df.apply(canonical, axis=1)

    # 4) Remove blank / placeholder answers and answers not in the option list
    missing = df["selected_option"].isna()
    invalid = df["selected_option"].str.lower().isin(INVALID_VALUES).fillna(False)

    # "Q1|Nova"-style keys make the "is this a real option?" check one fast lookup
    allowed = {f"{qid}|{opt}" for qid, q in config.QUESTIONS.items() for opt in q["options"]}
    keys = df["question_id"].fillna("") + "|" + df["selected_option"].fillna("")
    known_question = df["question_id"].isin(config.QUESTIONS.keys())
    off_list = known_question & ~keys.isin(allowed) & ~missing & ~invalid
    log["removed_missing_answer"] = int(missing.sum())
    log["removed_invalid_answer"] = int(invalid.sum() + off_list.sum())
    df = df[~(missing | invalid | off_list)]

    # 5) Duplicates: one answer per respondent per question (keep the first)
    before = len(df)
    df = df.drop_duplicates(subset=["respondent_id", "question_id"], keep="first")
    log["removed_duplicates"] = before - len(df)

    # 6) Missing demographics -> "Unknown" (we don't throw away the vote)
    for col in config.DEMOGRAPHIC_COLUMNS:
        log[f"filled_unknown_{col}"] = int(df[col].isna().sum())
        df[col] = df[col].fillna("Unknown")

    # 7) Dates
    df["response_date"] = pd.to_datetime(df["response_date"], errors="coerce", format="mixed")
    log["unparseable_dates"] = int(df["response_date"].isna().sum())

    df = df.sort_values(["response_date", "respondent_id", "question_id"]).reset_index(drop=True)
    log["rows_out"] = len(df)
    log["respondents"] = int(df["respondent_id"].nunique())

    if verbose:
        print("[cleaning] summary")
        for k, v in log.items():
            print(f"   {k:<28} {v:>7,}")
    return df, log
