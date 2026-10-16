"""
main.py - runs the full Poll Results Visualizer pipeline.

    poll data -> cleaning -> analysis -> charts -> insights report

Usage
-----
    python main.py                         # generate synthetic data and run everything
    python main.py --respondents 5000      # bigger synthetic poll
    python main.py --input data/raw/my_google_form.csv   # use your own CSV
"""

import argparse
import json

from src import analysis, config, visualization
from src.data_cleaning import clean_poll_data
from src.data_generator import generate_poll_data, to_google_form_format
from src.data_loader import load_poll_data
from src.insights import build_report, generate_insights


def parse_args():
    p = argparse.ArgumentParser(description="Poll Results Visualizer")
    p.add_argument("--input", help="Path to a poll CSV (long format or Google Form export). "
                                   "If omitted, synthetic data is generated.")
    p.add_argument("--respondents", type=int, default=2000,
                   help="Number of synthetic respondents (default 2000)")
    p.add_argument("--seed", type=int, default=config.RANDOM_SEED, help="Random seed")
    return p.parse_args()


def main():
    args = parse_args()
    for folder in [config.DATA_RAW_DIR, config.DATA_PROCESSED_DIR,
                   config.OUTPUTS_DIR, config.IMAGES_DIR]:
        folder.mkdir(parents=True, exist_ok=True)

    # ---- Phase 2: data input ------------------------------------------------
    print("=" * 60, "\nSTEP 1/5  Loading poll data")
    if args.input:
        raw = load_poll_data(args.input)
    else:
        raw = generate_poll_data(n_respondents=args.respondents, seed=args.seed)
        raw.to_csv(config.RAW_DATA_FILE, index=False)
        to_google_form_format(raw).to_csv(config.GOOGLE_FORM_SAMPLE_FILE, index=False)
        print(f"   synthetic data saved -> {config.RAW_DATA_FILE.relative_to(config.ROOT_DIR)}")
    print(f"   raw rows: {len(raw):,}")
    print(raw.head(5).to_string(index=False))

    # ---- Phase 3: cleaning --------------------------------------------------
    print("=" * 60, "\nSTEP 2/5  Cleaning")
    df, log = clean_poll_data(raw)
    df.to_csv(config.CLEAN_DATA_FILE, index=False)

    # ---- Phase 4-5: analysis ------------------------------------------------
    print("=" * 60, "\nSTEP 3/5  Analysis")
    pq = config.PRIMARY_QUESTION
    summary = analysis.overall_summary(df)
    print(json.dumps(summary, indent=3))

    for qid in config.QUESTIONS:
        if qid not in df["question_id"].unique():
            continue
        shares = analysis.option_share(df, qid)
        shares.to_csv(config.OUTPUTS_DIR / f"option_share_{qid.lower()}.csv", index=False)
        print(f"\n{qid}: {config.QUESTIONS[qid]['text']}")
        print(shares.sort_values("rank").to_string(index=False))

    for by in config.DEMOGRAPHIC_COLUMNS:
        analysis.segment_share(df, pq, by).to_csv(
            config.OUTPUTS_DIR / f"{pq.lower()}_share_by_{by}.csv")
        analysis.segment_leaders(df, pq, by).to_csv(
            config.OUTPUTS_DIR / f"{pq.lower()}_leaders_by_{by}.csv", index=False)
    analysis.trend_share(df, pq).to_csv(config.OUTPUTS_DIR / f"{pq.lower()}_weekly_trend.csv")
    analysis.satisfaction_score(df, "Q2", by="region").to_csv(
        config.OUTPUTS_DIR / "satisfaction_by_region.csv")
    analysis.satisfaction_score(df, "Q2", by="age_group").to_csv(
        config.OUTPUTS_DIR / "satisfaction_by_age_group.csv")

    lead = analysis.lead_analysis(df, pq)
    print("\nLead analysis:", json.dumps(lead, indent=3))

    # ---- Phase 6: visualization --------------------------------------------
    print("=" * 60, "\nSTEP 4/5  Creating charts")
    paths = visualization.create_all_charts(df)
    for p in paths:
        print(f"   saved {p.relative_to(config.ROOT_DIR)}")

    # ---- Phase 7: insights --------------------------------------------------
    print("=" * 60, "\nSTEP 5/5  Insights")
    for i, text in enumerate(generate_insights(df), start=1):
        print(f" {i}. {text.replace('**', '')}")
    report_path = config.OUTPUTS_DIR / "insights_report.md"
    report_path.write_text(build_report(df, log, paths), encoding="utf-8")
    print(f"\nReport saved -> {report_path.relative_to(config.ROOT_DIR)}")
    print("Done. Launch the interactive dashboard with:  streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
