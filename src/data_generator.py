"""
data_generator.py
-----------------
Creates a realistic SYNTHETIC poll dataset, so the project works without access
to any private survey system.

How the simulation works (short version):
1. Create N respondents and give each a region, age group, gender and date.
2. Every question has BASE probabilities for its options (the "true" opinion).
3. Those probabilities are NUDGED by region, age group and time, so the data
   contains real patterns for the analysis to discover.
4. Each respondent's answer is drawn randomly from their adjusted probabilities.
5. Optionally, real-world "dirt" is injected (duplicates, blanks, typos) so the
   cleaning step has genuine work to do.
"""

import numpy as np
import pandas as pd

from src import config

# ---------------------------------------------------------------------------
# Base opinion of the whole population (probabilities sum to 1 per question)
# ---------------------------------------------------------------------------
BASE_PROBS = {
    "Q1": [0.30, 0.26, 0.20, 0.16, 0.08],  # Nova, Pixelon, Orbit, Zenith, Other
    "Q2": [0.22, 0.36, 0.22, 0.13, 0.07],  # Very Satisfied ... Very Dissatisfied
    "Q3": [0.28, 0.24, 0.26, 0.14, 0.08],  # Battery, Camera, Price, Perf., Design
}

# ---------------------------------------------------------------------------
# Patterns hidden in the data. Values are ADDED to the base probabilities
# (then everything is re-normalised). Positive = more popular in that group.
# ---------------------------------------------------------------------------
REGION_BIAS = {
    "Q1": {
        "North":   [+0.08, -0.04, 0.00, -0.02, -0.02],  # Nova stronghold
        "South":   [-0.06, +0.10, -0.02, 0.00, -0.02],  # Pixelon stronghold
        "East":    [0.00, -0.02, +0.08, -0.04, -0.02],  # Orbit does well
        "West":    [+0.02, +0.02, -0.04, +0.02, -0.02],
        "Central": [-0.04, 0.00, 0.00, +0.06, -0.02],   # Zenith does well
    },
    "Q2": {
        "North":   [+0.04, +0.02, 0.00, -0.04, -0.02],
        "South":   [-0.04, -0.02, 0.00, +0.04, +0.02],  # less satisfied
    },
}

AGE_BIAS = {
    "Q1": {
        "18-24": [-0.06, +0.08, +0.04, -0.04, -0.02],  # young -> Pixelon/Orbit
        "25-34": [0.00, +0.04, +0.02, -0.04, -0.02],
        "45-54": [+0.04, -0.04, -0.02, +0.04, -0.02],
        "55+":   [+0.08, -0.08, -0.04, +0.06, -0.02],  # older -> Nova/Zenith
    },
    "Q3": {
        "18-24": [0.00, +0.08, +0.04, +0.02, +0.02],   # young care about camera
        "25-34": [0.00, +0.06, 0.00, +0.02, 0.00],
        "45-54": [+0.06, -0.04, +0.02, -0.02, -0.02],
        "55+":   [+0.10, -0.06, +0.04, -0.04, -0.02],  # older care about battery
    },
}

# Momentum over the polling window: Pixelon gains, Nova slowly loses.
# Value = total change in probability from the first to the last day.
TIME_DRIFT = {"Q1": [-0.06, +0.08, 0.00, -0.02, 0.00]}


def _adjusted_probs(qid, region, age_group, progress):
    """Return answer probabilities for one respondent.

    progress: 0.0 on the first day of the poll -> 1.0 on the last day.
    """
    probs = np.array(BASE_PROBS[qid], dtype=float)
    probs += np.array(REGION_BIAS.get(qid, {}).get(region, [0] * len(probs)))
    probs += np.array(AGE_BIAS.get(qid, {}).get(age_group, [0] * len(probs)))
    probs += np.array(TIME_DRIFT.get(qid, [0] * len(probs))) * progress
    probs = np.clip(probs, 0.01, None)  # no negative / zero probabilities
    return probs / probs.sum()          # re-normalise so they sum to 1


def generate_poll_data(n_respondents=2000, start_date="2026-01-05", days=56,
                       seed=config.RANDOM_SEED, add_noise=True):
    """Generate a long-format poll dataset (one row per answer).

    Parameters
    ----------
    n_respondents : number of simulated people
    start_date    : first day of the polling window
    days          : length of the polling window (56 days = 8 weeks)
    seed          : random seed for reproducibility
    add_noise     : inject duplicates / blanks / typos to mimic messy exports
    """
    rng = np.random.default_rng(seed)

    # --- Step 1: respondents and their demographics -----------------------
    respondents = pd.DataFrame({
        "respondent_id": [f"R{i:05d}" for i in range(1, n_respondents + 1)],
        "region": rng.choice(config.REGIONS, n_respondents, p=config.REGION_WEIGHTS),
        "age_group": rng.choice(config.AGE_GROUPS, n_respondents, p=config.AGE_WEIGHTS),
        "gender": rng.choice(config.GENDERS, n_respondents, p=config.GENDER_WEIGHTS),
        "day_offset": rng.integers(0, days, n_respondents),
    })
    respondents["response_date"] = (
        pd.Timestamp(start_date) + pd.to_timedelta(respondents["day_offset"], unit="D")
    )

    # --- Step 2-4: every respondent answers every question ----------------
    rows = []
    for r in respondents.itertuples(index=False):
        progress = r.day_offset / max(days - 1, 1)
        for qid, q in config.QUESTIONS.items():
            probs = _adjusted_probs(qid, r.region, r.age_group, progress)
            answer = rng.choice(q["options"], p=probs)
            rows.append({
                "respondent_id": r.respondent_id,
                "response_date": r.response_date.strftime("%Y-%m-%d"),
                "region": r.region,
                "age_group": r.age_group,
                "gender": r.gender,
                "question_id": qid,
                "question": q["text"],
                "selected_option": answer,
            })
    df = pd.DataFrame(rows, columns=config.LONG_COLUMNS)

    # --- Step 5: make it messy, like a real export -------------------------
    if add_noise:
        df = _inject_noise(df, rng)

    return df


def _inject_noise(df, rng):
    """Add the kind of problems found in real survey exports."""
    df = df.copy()
    n = len(df)

    # 1) Inconsistent text: extra spaces and random upper/lower case
    idx = rng.choice(n, int(n * 0.04), replace=False)
    df.loc[idx, "region"] = df.loc[idx, "region"].map(
        lambda s: rng.choice([s.upper(), s.lower(), f"  {s} "]))
    idx = rng.choice(n, int(n * 0.03), replace=False)
    df.loc[idx, "selected_option"] = df.loc[idx, "selected_option"].map(
        lambda s: rng.choice([s.lower(), f" {s}  "]))

    # 2) Missing answers (people skip questions)
    idx = rng.choice(n, int(n * 0.015), replace=False)
    df.loc[idx, "selected_option"] = np.nan

    # 3) Invalid answers (placeholder values from forms)
    idx = rng.choice(n, int(n * 0.005), replace=False)
    df.loc[idx, "selected_option"] = rng.choice(["N/A", "-", "???"], len(idx))

    # 4) Missing demographic values
    idx = rng.choice(n, int(n * 0.01), replace=False)
    df.loc[idx, "age_group"] = np.nan

    # 5) Duplicate submissions (form submitted twice)
    dupes = df.sample(frac=0.02, random_state=int(rng.integers(1e6)))
    df = pd.concat([df, dupes], ignore_index=True)

    # Shuffle so duplicates are not all at the bottom
    return df.sample(frac=1, random_state=int(rng.integers(1e6))).reset_index(drop=True)


def to_google_form_format(df_long, n_rows=200):
    """Convert long data into the WIDE layout of a Google Forms CSV export.

    Google Forms gives one row per respondent and one column per question,
    with a 'Timestamp' column. This sample file lets you test the loader on
    the same shape your own Google Form will produce.
    """
    ids = df_long["respondent_id"].drop_duplicates().head(n_rows)
    sub = df_long[df_long["respondent_id"].isin(ids)]
    # one row per respondent: demographics + one column per question
    people = sub.groupby("respondent_id")[["response_date", "region", "age_group",
                                           "gender"]].first()
    answers = sub.pivot_table(index="respondent_id", columns="question",
                              values="selected_option", aggfunc="first")
    wide = people.join(answers).reset_index()
    wide.columns.name = None
    wide["Timestamp"] = pd.to_datetime(wide["response_date"]).dt.strftime("%m/%d/%Y 10:15:00")
    wide = wide.drop(columns=["respondent_id", "response_date"]).rename(columns={
        "region": "Region", "age_group": "Age Group", "gender": "Gender"})
    first = ["Timestamp", "Region", "Age Group", "Gender"]
    return wide[first + [c for c in wide.columns if c not in first]]


if __name__ == "__main__":
    data = generate_poll_data()
    print(data.head(10))
    print(f"\nGenerated {len(data):,} rows")
