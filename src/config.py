"""
config.py
---------
Central place for every setting used in the project: folder paths, the poll
questions, answer options and demographic categories.

Keeping these in ONE file means you can change the poll (e.g. turn it into an
election poll or an employee survey) without touching the analysis code.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Folder paths (resolved relative to the project root, so it works anywhere)
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
OUTPUTS_DIR = ROOT_DIR / "outputs"
IMAGES_DIR = ROOT_DIR / "images"

RAW_DATA_FILE = DATA_RAW_DIR / "poll_responses_raw.csv"
GOOGLE_FORM_SAMPLE_FILE = DATA_RAW_DIR / "sample_google_form_export.csv"
CLEAN_DATA_FILE = DATA_PROCESSED_DIR / "poll_responses_clean.csv"

# Seed makes the synthetic data reproducible: same seed -> same dataset.
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Poll definition
# The scenario: a consumer-research poll about smartphones.
# Brand names are fictional so the project never misrepresents real companies.
# ---------------------------------------------------------------------------
QUESTIONS = {
    "Q1": {
        "text": "Which smartphone brand would you buy next?",
        "options": ["Nova", "Pixelon", "Orbit", "Zenith", "Other"],
        "type": "single_choice",
    },
    "Q2": {
        "text": "How satisfied are you with your current phone?",
        "options": [
            "Very Satisfied",
            "Satisfied",
            "Neutral",
            "Dissatisfied",
            "Very Dissatisfied",
        ],
        "type": "likert",  # ordered scale -> we also compute a satisfaction score
    },
    "Q3": {
        "text": "Which feature matters most when buying a phone?",
        "options": ["Battery Life", "Camera", "Price", "Performance", "Design"],
        "type": "single_choice",
    },
}

# The question used for "headline" results (leader, trend, pie chart).
PRIMARY_QUESTION = "Q1"

# Likert scale scores (5 = best). Used for the satisfaction score / NPS-style KPI.
LIKERT_SCORES = {
    "Very Satisfied": 5,
    "Satisfied": 4,
    "Neutral": 3,
    "Dissatisfied": 2,
    "Very Dissatisfied": 1,
}

# ---------------------------------------------------------------------------
# Demographics
# ---------------------------------------------------------------------------
REGIONS = ["North", "South", "East", "West", "Central"]
REGION_WEIGHTS = [0.24, 0.22, 0.18, 0.20, 0.16]  # share of respondents per region

AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]
AGE_WEIGHTS = [0.22, 0.30, 0.22, 0.15, 0.11]

GENDERS = ["Male", "Female", "Non-binary"]
GENDER_WEIGHTS = [0.49, 0.48, 0.03]

DEMOGRAPHIC_COLUMNS = ["region", "age_group", "gender"]

# Column names of the tidy ("long") format used everywhere in the project.
# One row = one answer by one respondent to one question.
LONG_COLUMNS = [
    "respondent_id",
    "response_date",
    "region",
    "age_group",
    "gender",
    "question_id",
    "question",
    "selected_option",
]

# 95% confidence -> z = 1.96 (used for margin of error)
Z_95 = 1.96
