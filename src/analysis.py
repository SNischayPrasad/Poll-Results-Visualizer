"""
analysis.py
-----------
All the numbers behind the charts:

- overall_summary      : KPIs (respondents, responses, date range)
- option_share         : votes, % share, rank and 95% margin of error per option
- lead_analysis        : leader vs runner-up and whether the lead is significant
- segment_share        : % share of each option inside each region / age group
- segment_leaders      : the winning option in every segment
- trend_share          : weekly share of each option (momentum over time)
- satisfaction_score   : average Likert score (1-5) and % satisfied, by segment
- association_test     : chi-square test - does the answer depend on the segment?
"""

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

from src import config


def _question_df(df, qid):
    return df[df["question_id"] == qid]


def overall_summary(df):
    return {
        "total_respondents": int(df["respondent_id"].nunique()),
        "total_responses": int(len(df)),
        "questions": int(df["question_id"].nunique()),
        "start_date": df["response_date"].min().date().isoformat(),
        "end_date": df["response_date"].max().date().isoformat(),
        "regions": int(df["region"].nunique()),
    }


def option_share(df, qid):
    """Vote count, percentage share and 95% margin of error for each option.

    Margin of error (MoE) for a proportion p from n answers:
        MoE = 1.96 * sqrt(p * (1 - p) / n)
    It tells us how much the share could move if we polled a different sample.
    """
    q = _question_df(df, qid)
    n = len(q)
    counts = q["selected_option"].value_counts()

    # keep the official option order when the question is known
    order = config.QUESTIONS.get(qid, {}).get("options")
    if order:
        counts = counts.reindex(order, fill_value=0)

    out = counts.rename("votes").to_frame()
    out["share_pct"] = out["votes"] / n * 100
    p = out["share_pct"] / 100
    out["moe_pct"] = config.Z_95 * np.sqrt(p * (1 - p) / n) * 100
    out["ci_low_pct"] = (out["share_pct"] - out["moe_pct"]).clip(lower=0)
    out["ci_high_pct"] = out["share_pct"] + out["moe_pct"]
    out["rank"] = out["votes"].rank(ascending=False, method="min").astype(int)
    out.index.name = "option"
    return out.round(2).reset_index()


def lead_analysis(df, qid):
    """Is the leader *really* ahead, or is it a statistical tie?

    The margin of error of the DIFFERENCE between two options from the same
    sample is: 1.96 * sqrt((p1 + p2 - (p1 - p2)^2) / n)
    If the lead is bigger than that, it is statistically significant (95%).
    """
    shares = option_share(df, qid).sort_values("votes", ascending=False)
    n = int(shares["votes"].sum())
    first, second = shares.iloc[0], shares.iloc[1]
    p1, p2 = first["share_pct"] / 100, second["share_pct"] / 100
    lead = (p1 - p2) * 100
    moe_diff = config.Z_95 * np.sqrt((p1 + p2 - (p1 - p2) ** 2) / n) * 100
    return {
        "leader": first["option"],
        "leader_share": round(first["share_pct"], 2),
        "runner_up": second["option"],
        "runner_up_share": round(second["share_pct"], 2),
        "lead_pct_points": round(lead, 2),
        "lead_moe_pct_points": round(moe_diff, 2),
        "significant": bool(lead > moe_diff),
        "sample_size": n,
    }


def segment_share(df, qid, by):
    """Row-percentage table: share of each option within each segment."""
    q = _question_df(df, qid)
    table = pd.crosstab(q[by], q["selected_option"], normalize="index") * 100
    order = config.QUESTIONS.get(qid, {}).get("options")
    if order:
        table = table.reindex(columns=[o for o in order if o in table.columns])
    if by == "age_group":
        rows = [a for a in config.AGE_GROUPS if a in table.index]
        table = table.reindex(rows + [r for r in table.index if r not in rows])
    return table.round(2)


def segment_counts(df, qid, by):
    q = _question_df(df, qid)
    return pd.crosstab(q[by], q["selected_option"])


def segment_leaders(df, qid, by):
    """Winning option, its share and the sample size in every segment."""
    shares = segment_share(df, qid, by)
    sizes = _question_df(df, qid).groupby(by).size()
    return pd.DataFrame({
        by: shares.index,
        "leader": shares.idxmax(axis=1).values,
        "leader_share_pct": shares.max(axis=1).round(2).values,
        "sample_size": sizes.reindex(shares.index).values,
    })


def trend_share(df, qid, freq="W-SUN"):
    """Share of each option per week. "W-SUN" = weeks ending Sunday, i.e. Mon-Sun weeks."""
    q = _question_df(df, qid).dropna(subset=["response_date"])
    period = q["response_date"].dt.to_period(freq).dt.start_time
    table = pd.crosstab(period, q["selected_option"], normalize="index") * 100
    order = config.QUESTIONS.get(qid, {}).get("options")
    if order:
        table = table.reindex(columns=[o for o in order if o in table.columns])
    table.index.name = "period_start"
    return table.round(2)


def satisfaction_score(df, qid="Q2", by=None):
    """Average Likert score (1-5) and % who are (Very) Satisfied."""
    q = _question_df(df, qid).copy()
    q["score"] = q["selected_option"].map(config.LIKERT_SCORES)
    q["is_satisfied"] = q["score"] >= 4
    q["is_dissatisfied"] = q["score"] <= 2
    agg = dict(avg_score=("score", "mean"), pct_satisfied=("is_satisfied", "mean"),
               pct_dissatisfied=("is_dissatisfied", "mean"), responses=("score", "size"))
    if by is None:
        return pd.Series({
            "avg_score": round(q["score"].mean(), 2),
            "pct_satisfied": round(q["is_satisfied"].mean() * 100, 2),
            "pct_dissatisfied": round(q["is_dissatisfied"].mean() * 100, 2),
            "responses": len(q),
        })
    res = q.groupby(by).agg(**agg)
    res[["pct_satisfied", "pct_dissatisfied"]] *= 100
    res["net_satisfaction"] = res["pct_satisfied"] - res["pct_dissatisfied"]
    return res.round(2).sort_values("avg_score", ascending=False)


def association_test(df, qid, by):
    """Chi-square test of independence between answer and a demographic.

    p < 0.05  -> the answer distribution really differs between segments.
    Cramer's V -> strength of that relationship. Cohen's thresholds depend on
                  table size: small/medium/large = 0.1/0.3/0.5 divided by
                  sqrt(min(rows, cols) - 1). For a 5x5 table: 0.05/0.15/0.25.
    """
    table = segment_counts(df, qid, by)
    table = table.loc[table.index != "Unknown"]
    chi2, p, dof, _ = chi2_contingency(table)
    n = table.to_numpy().sum()
    k = min(table.shape) - 1
    cramers_v = np.sqrt(chi2 / (n * k))
    small, medium, large = (t / np.sqrt(k) for t in (0.1, 0.3, 0.5))
    effect = ("negligible" if cramers_v < small else "small" if cramers_v < medium
              else "medium" if cramers_v < large else "large")
    return {"question_id": qid, "segment": by, "chi2": round(chi2, 2), "dof": int(dof),
            "p_value": float(f"{p:.3g}"), "cramers_v": round(cramers_v, 3),
            "effect_size": effect, "significant": bool(p < 0.05)}
