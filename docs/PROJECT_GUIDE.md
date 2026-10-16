# Poll Results Visualizer: Complete Project Guide

This guide covers everything you need to understand, run, explain, upload and defend this project in interviews. The code lives in `src/`, `main.py` and `dashboard/app.py`. This document explains the **why** behind it.

**Contents**
1. Project explanation · 2. Tech stack options · 3. Architecture · 4. Implementation plan · 5. Folder structure · 6. Installation · 7. Code walkthrough · 8. Virtual simulation · 9. How to run · 10. GitHub upload · 11. README · 12. Proof-building plan · 13. Screenshots checklist · 14. Interview preparation · 15. Future improvements · 16. Troubleshooting

---

## 1️⃣ Project explanation

### What is a Poll Results Visualizer?

**Simple explanation:** People answer a poll ("Which phone brand will you buy next?"). You end up with thousands of rows in a spreadsheet. A Poll Results Visualizer turns those rows into answers you can see at a glance: *Pixelon is winning with 31.5%, but Nova wins in the North, and Pixelon is gaining every week.*

**Technical explanation:** It is a data pipeline that ingests survey response data (respondent-level, categorical), validates and normalizes it, aggregates it into frequency and proportion tables (overall, by segment and by time period), quantifies sampling uncertainty (margin of error and confidence intervals), tests whether differences between segments are statistically significant (chi-square test of independence and Cramér's V), and presents the results as static charts, an interactive dashboard and an auto-generated narrative report.

### Why is it important?

- **Raw data is unreadable.** 6,000 rows mean nothing to a manager, but one chart does.
- **Raw data is dirty.** Duplicate submissions and typos silently distort results unless someone cleans them.
- **Percentages without uncertainty mislead.** A 2-point lead with a ±3-point margin of error is a *tie*, not a win.
- **Averages hide segments.** A brand can lead nationally and still lose two regions.
- **Speed.** An automated pipeline re-runs in seconds when new responses arrive.

### How organizations use it

| Organization | Use |
|---|---|
| Polling agencies / media | Election and opinion polls, published with margins of error |
| Marketing / product teams | Brand preference, feature prioritization, concept testing |
| HR / People analytics | Employee engagement (eNPS) and satisfaction surveys, broken down by department |
| Customer experience teams | CSAT / NPS surveys after purchases or support calls |
| Universities / event organizers | Course feedback, event feedback, session ratings |

### Real-world use cases

- **Election poll analysis:** candidate vote share, lead vs margin of error, swing regions, trends before election day.
- **Customer feedback surveys:** satisfaction scores by store/region, top complaint categories, change after a product launch.
- **Employee satisfaction surveys:** satisfaction by department/tenure, early warning of attrition risk in specific teams.
- **Product preference analysis:** which feature or flavour or design wins, and with which age group.
- **Classroom / event feedback:** session ratings, speaker comparison, what to improve next time.

> The same code handles all of these. You only change `QUESTIONS` in `src/config.py`.

### Workflow

```
poll data input → preprocessing → analysis → visualization → insights → decision-making
   (CSV/Form)      (clean, dedupe)  (shares, MoE,   (charts,        (auto text)   (e.g. "run a campaign
                                     segments, trend, dashboard)                    in the North")
                                     significance)
```

---

## 2️⃣ Tech stack options

| | **Option A: Easy** | **Option B: Intermediate** ✅ | **Option C: Advanced** |
|---|---|---|---|
| Language/tools | Excel / Google Sheets, or Python + Pandas in one notebook | Python, Pandas, NumPy, SciPy, modular `src/` package, Jupyter | Python + SQL (PostgreSQL), FastAPI, Airflow/cron, Docker |
| Visualization | Excel charts / Matplotlib | Matplotlib + Seaborn (static), Plotly (interactive) | Plotly Dash / Power BI / Tableau |
| Dashboard | ❌ | ✅ Streamlit | ✅ Deployed web app with live data |
| Statistics | Counts and % only | % + margin of error + chi-square | + survey weighting, Bayesian estimates, forecasting |
| Data | Static CSV | Synthetic generator + CSV + Google Form exports | Live API (Google Forms/Sheets, Typeform) + database |
| Difficulty | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Time | 1–2 days | 5 days | 2–4 weeks |

**Selected: Option B.** It is achievable in a week by a student, it shows *real* skills that recruiters screen for (Pandas, statistics, visualization, clean code, a dashboard), and it can grow into Option C later. Option A is too thin to stand out. Option C takes a long time, and recruiters mostly can't run it.

---

## 3️⃣ Project architecture

### Input (one row = one answer)

| Column | Example | Meaning |
|---|---|---|
| respondent_id | R00042 | unique person |
| response_date | 2026-01-14 | when they answered |
| region | North | demographic |
| age_group | 25-34 | demographic |
| gender | Female | demographic |
| question_id | Q1 | short question code |
| question | Which smartphone brand would you buy next? | full text |
| selected_option | Pixelon | the answer |

This is called **long (tidy) format**. Google Forms gives **wide format** (one row per person, one column per question). `data_loader.py` converts wide to long automatically using `melt`.

### Processing

1. **Data cleaning:** trim and title-case text, map answers to the official options, remove blank/invalid/duplicate answers, fill missing demographics with `Unknown`, parse dates.
2. **Grouping:** `groupby` / `crosstab` by question, region, age group, gender and week.
3. **Aggregation:** vote counts per option.
4. **Percentage calculation:** share = votes / total answers × 100, plus a 95% margin of error.
5. **Comparative analysis:** segment shares, segment winners, leader vs runner-up significance, chi-square test, weekly trend, satisfaction score.

### Output

- **Charts:** 12 PNGs in `images/`
- **Dashboard:** `dashboard/app.py` (Streamlit) plus the static `images/dashboard_summary.png`
- **Summary tables:** CSVs in `outputs/`
- **Insights:** `outputs/insights_report.md`

### Text architecture diagram

```
┌──────────────────────────── INPUT LAYER ─────────────────────────────┐
│  data_generator.py         data_loader.py                            │
│  (synthetic poll)          (your CSV / Google Form export)           │
│        │                         │  wide → long (melt)               │
│        └────────────┬────────────┘                                   │
└─────────────────────┼────────────────────────────────────────────────┘
                      ▼   data/raw/poll_responses_raw.csv
┌──────────────────────────── PROCESSING LAYER ────────────────────────┐
│  data_cleaning.py  → trim/standardize → validate options → dedupe    │
│                    → fill Unknown → parse dates → cleaning log       │
│                      ▼   data/processed/poll_responses_clean.csv     │
│  analysis.py       → option_share (+MoE) → lead_analysis             │
│                    → segment_share / segment_leaders                 │
│                    → trend_share → satisfaction_score                │
│                    → association_test (chi-square, Cramér's V)       │
└─────────────────────┼────────────────────────────────────────────────┘
                      ▼
┌──────────────────────────── OUTPUT LAYER ────────────────────────────┐
│  visualization.py → images/*.png          dashboard/app.py → browser │
│  insights.py      → outputs/insights_report.md   outputs/*.csv       │
└──────────────────────────────────────────────────────────────────────┘
                      ▼
               Decision-making (stakeholder reads report/dashboard)
```

### Data flow explanation

`main.py` orchestrates everything. It (1) gets raw data from the generator or the loader, (2) passes it to `clean_poll_data`, which returns a clean DataFrame and a log, (3) saves the clean CSV, (4) calls the `analysis` functions and saves their tables, (5) calls `visualization.create_all_charts`, and (6) calls `insights.build_report`. The dashboard reuses the **same** `analysis` functions, so the numbers in the dashboard and the report always agree.

---

## 4️⃣ Implementation plan (phase-wise)

| Phase | What to do | Why | Expected output | Mistakes to avoid |
|---|---|---|---|---|
| **1. Setup** | Install Python, create folder structure, virtual env, `requirements.txt`, `git init` | Reproducible environment; anyone can run your code | Folders + activated `.venv` | Installing into global Python; committing `.venv/` |
| **2. Data creation/input** | Define questions in `config.py`; write the generator; also support CSV / Google Form | You need data with *known* patterns to prove the analysis works | `data/raw/poll_responses_raw.csv` (~6,000 rows) | Purely uniform random data (no patterns = boring insights); no seed (results change every run) |
| **3. Cleaning** | Standardize text, validate options, remove blanks/invalid/duplicates, parse dates, log every step | Garbage in = garbage out | `data/processed/poll_responses_clean.csv` + cleaning log | Dropping whole respondents for one missing field; silently deleting rows without logging |
| **4. EDA** | Shape, dtypes, missing values, respondent mix by region/age/week (notebook) | Understand the sample before trusting results | Notebook outputs, demographic counts | Skipping EDA and missing a skewed sample |
| **5. Analysis** | Shares, MoE, lead significance, segments, trend, satisfaction, chi-square | Answers the business questions with evidence | CSV tables in `outputs/` | Using raw counts to compare segments of different sizes (use %); ignoring margin of error |
| **6. Visualization** | Bar, donut, stacked, heatmap, trend, dashboard | Humans read pictures faster than tables | PNGs in `images/` + Streamlit app | Rainbow colours, 3-D pies, missing titles/labels, a different colour for the same option across charts |
| **7. Insights** | Generate plain-English findings and recommendations | Stakeholders want "so what?", not charts alone | `outputs/insights_report.md` | Hard-coding conclusions; claiming causation from a poll |
| **8. GitHub upload** | README, screenshots, meaningful commits, push | It's your public proof of work | Public repo with rendered README | One giant "final" commit; no README; broken image links |

---

## 5️⃣ Folder structure

```
Poll-Results-Visualizer/
│
├── data/
│   ├── raw/           ← untouched input (generated or downloaded). Never edit by hand.
│   └── processed/     ← cleaned output of data_cleaning.py
├── notebooks/         ← Jupyter EDA notebook (exploration, step-by-step story)
├── src/               ← reusable Python modules (the "engine")
│   ├── config.py          settings: paths, questions, options, demographics
│   ├── data_generator.py  synthetic poll simulation
│   ├── data_loader.py     CSV + Google Form loader (wide → long)
│   ├── data_cleaning.py   cleaning pipeline + log
│   ├── analysis.py        all calculations
│   ├── visualization.py   all static charts
│   └── insights.py        narrative findings + Markdown report
├── dashboard/
│   └── app.py         ← Streamlit interactive dashboard
├── outputs/           ← summary tables (CSV) + insights_report.md
├── images/            ← charts (PNG) used by README and report
├── docs/
│   └── PROJECT_GUIDE.md   this file
├── README.md          ← GitHub landing page
├── requirements.txt   ← library list for pip
├── LICENSE            ← MIT license
├── .gitignore         ← files Git should ignore (.venv, caches)
└── main.py            ← one command runs the whole pipeline
```

**Why `src/` and not one big notebook?** Notebooks are for exploring. Modules are for reuse and testing. Recruiters look for both.

---

## 6️⃣ Installation guide

### Step 1: Install Python
- Download Python **3.10 or newer** from python.org.
- **Windows:** tick **"Add Python to PATH"** in the installer.
- Check it worked: `python --version` (Mac: `python3 --version`)

### Step 2: Get the project folder
```bash
cd path/to/Poll-Results-Visualizer
```

### Step 3: Create and activate a virtual environment
A virtual environment keeps this project's libraries separate from other projects.

**Windows (PowerShell / CMD):**
```bash
python -m venv .venv
.venv\Scripts\activate
```
If PowerShell blocks activation, run this once:
```bash
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Your prompt now starts with `(.venv)`.

### Step 4: Install libraries
```bash
pip install -r requirements.txt
```

### Step 5: Verify
```bash
python -c "import pandas, seaborn, scipy, plotly, streamlit; print('All good')"
```

---

## 7️⃣ Full project code: walkthrough

All code is in the repo and is fully commented. Here is what each file does and the key idea inside it.

| File | Key functions | Core idea |
|---|---|---|
| `src/config.py` | `QUESTIONS`, `REGIONS`, `AGE_GROUPS`, `LIKERT_SCORES` | Change the poll without touching logic |
| `src/data_generator.py` | `generate_poll_data()`, `_adjusted_probs()`, `_inject_noise()`, `to_google_form_format()` | Base probabilities + region/age/time nudges → sampled answers; then realistic dirt |
| `src/data_loader.py` | `load_poll_data()`, `wide_to_long()` | Detect format; `pd.melt` converts a Google Form into long format |
| `src/data_cleaning.py` | `clean_poll_data()` | 7 cleaning steps, each counted in a log |
| `src/analysis.py` | `option_share`, `lead_analysis`, `segment_share`, `segment_leaders`, `trend_share`, `satisfaction_score`, `association_test` | `value_counts`, `crosstab(normalize="index")`, MoE formula, `chi2_contingency` |
| `src/visualization.py` | `plot_option_share_bar`, `plot_option_share_pie`, `plot_segment_stacked`, `plot_segment_heatmap`, `plot_trend`, `plot_satisfaction_by`, `plot_dashboard` | Consistent colour per option, direct labels, error bars |
| `src/insights.py` | `generate_insights`, `recommendations`, `build_report` | Every sentence is computed from the data |
| `main.py` | `main()` | Orchestrates the 5 steps; CLI flags `--input`, `--respondents`, `--seed` |
| `dashboard/app.py` | Streamlit script | Filters → same analysis functions → Plotly charts |

### Key code snippets to understand (and explain in interviews)

**Percentage share + margin of error** (`analysis.option_share`):
```python
counts = q["selected_option"].value_counts()
share = counts / n * 100
moe   = 1.96 * np.sqrt(p * (1 - p) / n) * 100     # 95% confidence
```

**Segment comparison** (`analysis.segment_share`):
```python
pd.crosstab(q["region"], q["selected_option"], normalize="index") * 100
# each row (region) sums to 100% → fair comparison across regions of different sizes
```

**Is the lead real?** (`analysis.lead_analysis`):
```python
moe_diff = 1.96 * np.sqrt((p1 + p2 - (p1 - p2)**2) / n) * 100
significant = lead > moe_diff
```

**Does the answer depend on region?** (`analysis.association_test`):
```python
chi2, p, dof, _ = chi2_contingency(pd.crosstab(q["region"], q["selected_option"]))
cramers_v = np.sqrt(chi2 / (n * (min(table.shape) - 1)))
```

**Google Form → long format** (`data_loader.wide_to_long`):
```python
df.melt(id_vars=["respondent_id", "response_date", "region", "age_group", "gender"],
        var_name="question", value_name="selected_option")
```

---

## 8️⃣ Virtual simulation (how the synthetic poll is built)

You don't have access to an enterprise survey platform, so you **simulate** one. Because you plant the patterns yourself, you can prove the analysis finds them. That is called **validating the pipeline against known ground truth**, and it is a strong interview talking point.

**Step 1: Define the poll.** Three questions in `config.QUESTIONS`: brand preference (single choice), satisfaction (5-point Likert), most important feature (single choice).

**Step 2: Create respondents.** 2,000 people. Each gets a region (weights 24/22/18/20/16%), an age group (22/30/22/15/11%), a gender, and a random day in an 8-week window. `numpy.random.default_rng(42)` makes it reproducible.

**Step 3: Set base opinion.** For example, brand base probabilities: Nova 30%, Pixelon 26%, Orbit 20%, Zenith 16%, Other 8%.

**Step 4: Plant demographic patterns.** Add nudges per segment (`REGION_BIAS`, `AGE_BIAS`):
- North +8 pts Nova · South +10 pts Pixelon · East +8 pts Orbit · Central +6 pts Zenith
- 18–24: +8 pts Pixelon · 55+: +8 pts Nova, +6 pts Zenith
- 18–24 care more about Camera; 55+ care more about Battery Life
- South is less satisfied, North more satisfied

**Step 5: Plant a trend.** `TIME_DRIFT`: across the 8 weeks Pixelon gains +8 pts and Nova loses −6 pts (scaled by how far into the window the response is).

**Step 6: Sample answers.** For each respondent and each question: probabilities = base + region nudge + age nudge + drift, clipped and re-normalized to sum to 1, then `rng.choice(options, p=probs)`.

**Step 7: Inject real-world mess.** 4% inconsistent region spelling (`NORTH`, `  north `), 3% messy answer text, 1.5% blank answers, 0.5% junk (`N/A`, `???`), 1% missing age group, and 2% duplicate submissions.

**Step 8: Clean.** The cleaning log shows exactly what was fixed: 6,120 rows in → 88 blank, 30 invalid and 120 duplicates removed, 60 unknown ages filled → 5,882 clean rows for 2,000 respondents.

**Step 9: Identify the leader.** `lead_analysis` sorts by votes and compares #1 vs #2 against the MoE of the difference. Result: Pixelon 31.5% vs Nova 27.6%, a lead of 4.0 > 3.4, so it is **significant**.

> Why does Pixelon lead when Nova had the higher base? Because the young-age boost, the South boost (South is a big region) and the upward drift add up. This is a great example of why you must analyze the data rather than assume.

**Step 10: Generate insights.** `insights.py` turns results into sentences. It recovers every planted pattern: North → Nova, East → Orbit, South → Pixelon; young → Pixelon, 45+ → Nova; Pixelon rising; South least satisfied; gender *not* significant (no gender pattern was planted, so a test that found one would be a red flag).

**Final output:** charts, dashboard, CSV tables and the insights report.

### What to screenshot, generate and save as proof

| Proof | How |
|---|---|
| Terminal run of `python main.py` | Screenshot the cleaning summary + lead analysis |
| Raw vs clean data | Notebook cells 1 and 3 (`raw.head()`, `df.head()`) |
| Summary table | `outputs/option_share_q1.csv` or notebook section 5 |
| All 12 charts | Already in `images/` |
| Dashboard | Screenshot of `streamlit run dashboard/app.py` with a filter applied |
| Report | `outputs/insights_report.md` rendered on GitHub |
| Git history | `git log --oneline` screenshot |

---

## 9️⃣ How to run the project

```bash
# activate your environment first (.venv\Scripts\activate  or  source .venv/bin/activate)

python main.py                                   # default: 2,000 synthetic respondents
python main.py --respondents 5000 --seed 7       # different/bigger poll
python main.py --input data/raw/sample_google_form_export.csv   # Google-Form-style CSV
streamlit run dashboard/app.py                   # interactive dashboard → http://localhost:8501
jupyter notebook notebooks/poll_analysis_eda.ipynb   # EDA walkthrough
```

**Expected terminal output (shortened):**
```
STEP 1/5  Loading poll data   → raw rows: 6,120
STEP 2/5  Cleaning            → rows_out 5,882, respondents 2,000
STEP 3/5  Analysis            → Pixelon 31.53% (±2.06), Nova 27.55% ...
                                 Lead analysis: significant = true
STEP 4/5  Creating charts     → 12 files saved in images/
STEP 5/5  Insights            → 12 findings, report saved
```

**Generated files**

| Folder | Files |
|---|---|
| `data/raw/` | `poll_responses_raw.csv`, `sample_google_form_export.csv` |
| `data/processed/` | `poll_responses_clean.csv` |
| `outputs/` | `option_share_q1/q2/q3.csv`, `q1_share_by_region/age_group/gender.csv`, `q1_leaders_by_*.csv`, `q1_weekly_trend.csv`, `satisfaction_by_region/age_group.csv`, `insights_report.md` |
| `images/` | `bar_q1_share.png`, `bar_q3_share.png`, `pie_q1_share.png`, `stacked_q1_by_region.png`, `stacked_q1_by_age_group.png`, `stacked_q2_by_region.png`, `heatmap_q1_by_age_group.png`, `heatmap_q3_by_age_group.png`, `trend_q1_weekly.png`, `net_satisfaction_by_region.png`, `net_satisfaction_by_age_group.png`, `dashboard_summary.png` |

---

## 🔟 GitHub upload steps

### Repo details
- **Name:** `Poll-Results-Visualizer`
- **Description:** `End-to-end poll & survey analytics in Python: data cleaning, vote share with margin of error, regional/demographic analysis, chi-square tests, trend charts, Streamlit dashboard and auto-generated insights.`
- **Topics/tags:** `data-analysis` `data-visualization` `survey-analysis` `pandas` `python` `matplotlib` `seaborn` `plotly` `streamlit` `dashboard` `statistics` `eda` `poll` `business-analytics` `portfolio-project`

### Step-by-step
1. Create a GitHub account → **New repository** → name `Poll-Results-Visualizer` → Public → **don't** add a README (you already have one) → Create.
2. Configure Git once on your computer:
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```
3. Connect and push:
   ```bash
   cd Poll-Results-Visualizer
   git init
   git add .
   git commit -m "Initial commit: project structure and requirements"
   git branch -M main
   git remote add origin https://github.com/Nischay2008/Poll-Results-Visualizer.git
   git push -u origin main
   ```
4. When GitHub asks for a password, use a **Personal Access Token** (Settings → Developer settings → Tokens), or sign in with GitHub Desktop / VS Code.
5. On the repo page: ⚙️ next to "About" → add the description and topics.
6. Pin the repo on your profile (Profile → Customize your pins).

### Good commit messages (one per day/feature)
```
chore: set up project structure, venv and requirements
feat: add synthetic poll data generator with regional/age patterns
feat: add Google Form CSV loader (wide to long)
feat: add data cleaning pipeline with cleaning log
feat: add vote share, margin of error and lead significance analysis
feat: add segment analysis, weekly trend and chi-square tests
feat: add bar, donut, stacked, heatmap and trend charts
feat: add Streamlit interactive dashboard
feat: generate insights report automatically
docs: add README with screenshots and results
```

---

## 1️⃣1️⃣ README.md

The full README is in the project root ([`README.md`](../README.md)). It contains: overview, problem, solution, features, tech stack, project structure, how to run, results table and insights, screenshots, how to use your own Google Form, future improvements and a disclaimer. **Before you publish, replace `Your Name`, `Nischay2008` and the LinkedIn link.**

---

## 1️⃣2️⃣ Proof-building strategy (5-day plan)

| Day | Work | Commits | Proof screenshot |
|---|---|---|---|
| **Day 1: Setup** | Install Python, create venv, folders, `requirements.txt`, `.gitignore`, `config.py`; create the GitHub repo and push | `chore: set up project structure, venv and requirements` | VS Code folder tree + `(.venv)` terminal |
| **Day 2: Dataset** | `data_generator.py` + `data_loader.py`; generate the raw CSV; make a real 10-question Google Form, collect 20–30 responses from friends, download the CSV | `feat: add synthetic poll data generator...`, `feat: add Google Form CSV loader` | `raw.head()` output; your Google Form responses page |
| **Day 3: Cleaning + analysis** | `data_cleaning.py`, `analysis.py`, notebook sections 1–7 | `feat: add data cleaning pipeline...`, `feat: add vote share, margin of error...`, `feat: add segment analysis...` | Cleaning log; summary table; lead analysis JSON |
| **Day 4: Charts** | `visualization.py`, `insights.py`, `dashboard/app.py` | `feat: add charts...`, `feat: add Streamlit dashboard`, `feat: generate insights report` | Every chart; dashboard with a filter applied |
| **Day 5: Final upload** | README, screenshots, run everything fresh, push; post on LinkedIn | `docs: add README with screenshots and results` | GitHub repo page, rendered README, commit history |

**LinkedIn post idea:** "Built a Poll Results Visualizer in Python 📊 It cleans messy survey data, calculates vote share *with margins of error*, finds regional and age patterns with chi-square tests, and serves everything in a Streamlit dashboard. Key learning: a 4-point lead only matters if it's bigger than the margin of error. [repo link] #DataAnalytics #Python"

---

## 1️⃣3️⃣ Screenshots / outputs checklist

Save each in `images/` (or a `screenshots/` folder) with these names:

| # | Capture | Where it comes from | Suggested file |
|---|---|---|---|
| 1 | Dataset preview (raw, messy) | Notebook §1 `raw.head(10)` (shows mixed case/blanks) | `ss_raw_data.png` |
| 2 | Cleaned dataset preview + cleaning log | Notebook §3 / terminal STEP 2 | `ss_clean_data.png` |
| 3 | Vote/share summary table | Terminal STEP 3 or notebook §5 | `ss_summary_table.png` |
| 4 | Bar chart | `images/bar_q1_share.png` | (auto) |
| 5 | Pie chart | `images/pie_q1_share.png` | (auto) |
| 6 | Region-wise chart | `images/stacked_q1_by_region.png` | (auto) |
| 7 | Demographic comparison chart | `images/heatmap_q1_by_age_group.png`, `stacked_q1_by_age_group.png` | (auto) |
| 8 | Trend chart | `images/trend_q1_weekly.png` | (auto) |
| 9 | Final dashboard | `images/dashboard_summary.png` + Streamlit screenshot with filters | `streamlit_dashboard.png` |
| 10 | GitHub repo preview | Your repo homepage with README rendered | `ss_github_repo.png` |

Tip: in Windows use **Win + Shift + S**; on Mac **Cmd + Shift + 4**. Use light mode in Streamlit (⋮ → Settings → Theme) for README screenshots.

---

## 1️⃣4️⃣ Interview preparation

### HR explanation (30 seconds, non-technical)
> "I built a tool that turns raw poll or survey responses into clear results and recommendations. It cleans the data, shows who's winning and by how much, checks whether that lead is real or just noise, and shows how opinions differ by region and age group and over time. Everything is in a dashboard a manager can filter. For example, it showed that a brand leading nationally was actually losing in two regions, which would change where you spend marketing money."

### Technical explanation (2 minutes)
> "It's a modular Python pipeline. Input is either a reproducible synthetic generator, where I planted known regional, age and time patterns to validate the pipeline, or any CSV including Google Forms exports, which I convert from wide to long format with `melt`. Cleaning standardizes text, validates answers against a whitelist, removes blanks, junk and duplicate submissions, and logs every step. Analysis uses Pandas `value_counts` and `crosstab` for shares; I add a 95% margin of error per option and a significance check on the lead using the variance of the difference between two multinomial proportions. For segments, I use row-normalized crosstabs plus a chi-square test of independence with Cramér's V for effect size. Visuals are Matplotlib/Seaborn for the report and Plotly/Streamlit for the interactive dashboard, both calling the same analysis functions so the numbers always match. Finally, `insights.py` writes a Markdown report whose every sentence is computed from the data."

### 10 interview questions with answers

**1. Why did you use synthetic data, and isn't that "fake"?**
I didn't have access to proprietary survey data, so I simulated it. And simulation has a real advantage: I *know* the true patterns I planted, such as North preferring Nova and Pixelon trending up. So I could verify the pipeline recovers them, and that it does **not** find a gender effect I never planted. That's validating the pipeline against known ground truth. The loader also accepts real Google Form exports. I tested it with one.

**2. What is margin of error and how did you calculate it?**
It's the range within which the true population share likely lies. For a share *p* from *n* responses at 95% confidence: MoE = 1.96 × √(p(1−p)/n). With n = 1,960, Pixelon's 31.5% has about ±2.1 pts. It shrinks with the square root of n: you need 4× the sample to halve it.

**3. How do you know the leader's lead is real?**
I compare the lead to the margin of error *of the difference*, not of each option. For two options from the same sample: 1.96 × √((p1 + p2 − (p1 − p2)²)/n). Pixelon's 4.0-pt lead exceeds the 3.4-pt MoE, so it's significant. If it didn't, I'd report a statistical tie. A common mistake is just checking whether the two confidence intervals overlap, which is too conservative.

**4. What cleaning steps did you perform and why?**
Trimming and title-casing (" NORTH " → "North"), mapping answers to official options case-insensitively, dropping blanks and placeholders like N/A, dropping answers not in the option list, de-duplicating on respondent + question (double submissions), filling missing demographics with "Unknown" so I don't throw away valid votes, and parsing dates. Every step is counted in a cleaning log for auditability.

**5. Why long format instead of wide?**
Long (tidy) format, with one row per answer, lets the same `groupby`/`crosstab` code work for any number of questions. Wide format would need code per column. Google Forms exports wide, so I `melt` it.

**6. What does the chi-square test tell you here?**
Whether answer choice is independent of a demographic. For region, p ≈ 4×10⁻⁸, so brand choice clearly depends on region. For gender, p = 0.20, so there is no evidence of a difference. I pair it with Cramér's V to measure strength, because with large samples even tiny differences become "significant". Here V ≈ 0.09, which for a 5×5 table is a small effect.

**7. Why percentages within segments rather than counts?**
Regions have different sizes (North has 24% of respondents, Central 16%). Raw counts would mostly reflect region size. Row-normalized percentages (`crosstab(normalize="index")`) make segments comparable.

**8. How did you choose your chart types?**
Horizontal bars for comparing options (easy to read labels, with error bars for uncertainty). A donut for part-of-whole with few categories. 100% stacked bars and heatmaps for segment comparisons. Lines for trends over time. A diverging blue-grey-red palette for the satisfaction scale because it has a direction. Each option keeps the same colour in every chart.

**9. What are the limitations of this analysis?**
The data is not weighted: if the sample over-represents young people, the totals are biased (fix: post-stratification/raking to census proportions). A poll is self-reported and shows association, not causation. Small segments (e.g. non-binary, n ≈ 60) have large margins of error. Weekly samples of ~250 are noisy, which is why I compare 2-week averages for momentum.

**10. How would you scale this for a real company?**
Pull responses automatically from the Google Sheets/Typeform API on a schedule, store them in a SQL database, add survey weighting, add tests (pytest) for the cleaning rules, containerize it, deploy the dashboard (Streamlit Cloud or Power BI), and add sentiment analysis for open-ended comments.

### Bonus quick-fire questions
- *Difference between `groupby` and `crosstab`?* `crosstab` is a convenience for frequency tables of two categorical columns. `groupby` is general split-apply-combine.
- *What is a Likert scale?* An ordered rating scale (Very Dissatisfied → Very Satisfied). I convert it to 1–5 scores for averages and net satisfaction (% satisfied − % dissatisfied).
- *Why set a random seed?* Reproducibility: the same seed gives the same dataset, so results in the README match what a recruiter gets when they run it.

---

## 1️⃣5️⃣ Future improvements

| Improvement | How you would do it |
|---|---|
| **Live polling integration** | Google Forms → linked Google Sheet → read with `gspread` / Google Sheets API (or Typeform/SurveyMonkey APIs) |
| **Streamlit dashboard upgrades** | Deploy free on Streamlit Community Cloud; add a question builder, login, and PDF export |
| **Sentiment analysis on open-ended responses** | Add a "comments" column; score with VADER/TextBlob or a transformer model; show sentiment by option/region; add a word cloud of top themes |
| **Demographic deep-dive** | Cross-segments (region × age), survey weighting (raking with census data), minimum sample size warnings |
| **Real-time result updates** | `st.cache_data(ttl=60)` + auto-refresh, or a FastAPI endpoint + WebSocket for live counts |
| **API integration** | A FastAPI service: `POST /responses`, `GET /results?question=Q1&region=North` |
| **Power BI dashboard** | Load `data/processed/poll_responses_clean.csv`; build DAX measures for share %, slicers for region/age/date |
| **Testing & CI** | `pytest` for the cleaning and analysis functions + a GitHub Actions workflow that runs them on every push |
| **Forecasting** | For election-style polls: poll-of-polls averaging and a simple trend forecast |

---

## 1️⃣6️⃣ Troubleshooting

| Error / problem | Cause | Solution |
|---|---|---|
| `'python' is not recognized` (Windows) | Python not on PATH | Reinstall and tick "Add Python to PATH", or use `py` instead of `python` |
| `ModuleNotFoundError: No module named 'pandas'` | venv not activated or libs not installed | Activate `.venv`, then `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'src'` | Running from the wrong folder | `cd` into the project root and run `python main.py` there (not inside `src/`) |
| PowerShell: "running scripts is disabled" | Execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `streamlit: command not found` | venv not active | Activate venv, or run `python -m streamlit run dashboard/app.py` |
| Dashboard shows old numbers | Streamlit cache | Press **C** in the app (clear cache) or re-run `python main.py`, then refresh |
| `FileNotFoundError: data/raw/...` | Pipeline not run yet | Run `python main.py` first (it creates the data) |
| `UnicodeDecodeError` reading your CSV | Excel saved it as ANSI | Re-save as "CSV UTF-8", or `pd.read_csv(path, encoding="latin-1")` |
| Your Google Form questions all show as "Other"/invalid | Their text/options aren't in `config.QUESTIONS` | Add them to `QUESTIONS` (exact question text gives the right ID), or they're analyzed with auto IDs (Q1, Q2…) |
| Demographics all "Unknown" in your CSV | Column names differ | Rename to `Region`, `Age Group`, `Gender`, or add aliases in `COLUMN_ALIASES` in `data_loader.py` |
| Charts look squashed / labels overlap | Long option names | Increase `figsize` in the relevant function in `visualization.py` |
| `git push` rejected (`fetch first`) | Repo created with a README on GitHub | `git pull origin main --rebase`, then `git push` |
| `git push` asks for a password and fails | GitHub no longer accepts passwords | Use a Personal Access Token or GitHub Desktop |
| Images not showing in README on GitHub | Wrong path or images not committed | Paths must be relative (`images/x.png`); `git add images/` and push |
| Results differ from the README | Different seed or respondent count | Use the defaults: `python main.py` (seed 42, 2,000 respondents) |
