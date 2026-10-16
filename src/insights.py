"""
insights.py
-----------
Turns the numbers into plain-English findings, the part a manager actually
reads. Every sentence is generated from the data, so if the data changes the
report changes too (no hard-coded conclusions).
"""

from datetime import datetime

from src import analysis, config


def _fmt_pct(x):
    return f"{x:.1f}%"


def generate_insights(df):
    """Return a list of insight strings."""
    pq = config.PRIMARY_QUESTION
    out = []

    # 1) Headline: who is leading and is the lead real?
    lead = analysis.lead_analysis(df, pq)
    verdict = ("a statistically significant lead" if lead["significant"]
               else "within the margin of error (a statistical tie)")
    out.append(
        f"**{lead['leader']}** is the most preferred next brand with "
        f"{_fmt_pct(lead['leader_share'])}, ahead of {lead['runner_up']} "
        f"({_fmt_pct(lead['runner_up_share'])}). The {lead['lead_pct_points']:.1f}-point gap is "
        f"{verdict} (95% MoE of the gap: +/-{lead['lead_moe_pct_points']:.1f} pts, "
        f"n = {lead['sample_size']:,}).")

    # 2) Regional winners
    leaders = analysis.segment_leaders(df, pq, "region")
    leaders = leaders[leaders["region"] != "Unknown"]
    upsets = leaders[leaders["leader"] != lead["leader"]]
    parts = ", ".join(f"{r.region}: {r.leader} ({_fmt_pct(r.leader_share_pct)})"
                      for r in leaders.itertuples())
    out.append(f"Regional winners - {parts}.")
    if len(upsets):
        out.append(
            f"{lead['leader']} does NOT win everywhere: "
            + "; ".join(f"{r.leader} leads in {r.region}" for r in upsets.itertuples())
            + ". Region-specific campaigns are recommended there.")

    # 3) Strongest / weakest region for the leader
    reg = analysis.segment_share(df, pq, "region")
    reg = reg.loc[reg.index != "Unknown", lead["leader"]]
    out.append(f"{lead['leader']} is strongest in {reg.idxmax()} ({_fmt_pct(reg.max())}) and "
               f"weakest in {reg.idxmin()} ({_fmt_pct(reg.min())}) - a "
               f"{reg.max() - reg.min():.1f}-point regional spread.")

    # 4) Age pattern
    age = analysis.segment_leaders(df, pq, "age_group")
    age = age[age["age_group"] != "Unknown"]
    out.append("By age group the leader is: " + ", ".join(
        f"{r.age_group} -> {r.leader} ({_fmt_pct(r.leader_share_pct)})"
        for r in age.itertuples()) + ".")

    # 5) Trend / momentum
    trend = analysis.trend_share(df, pq)
    if len(trend) >= 4:
        # compare the average of the first 2 weeks with the last 2 weeks
        # (single weeks have small samples, so averaging reduces noise)
        change = (trend.tail(2).mean() - trend.head(2).mean()).sort_values()
        gainer, loser = change.index[-1], change.index[0]
        out.append(f"Momentum: {gainer} gained {change.iloc[-1]:+.1f} pts from the first two "
                   f"weeks to the last two weeks, while {loser} moved {change.iloc[0]:+.1f} pts.")

    # 6) Satisfaction
    sat = analysis.satisfaction_score(df, "Q2")
    sat_reg = analysis.satisfaction_score(df, "Q2", by="region")
    sat_reg = sat_reg.loc[sat_reg.index != "Unknown"]
    out.append(f"Average satisfaction is {sat['avg_score']:.2f}/5; "
               f"{_fmt_pct(sat['pct_satisfied'])} are satisfied vs "
               f"{_fmt_pct(sat['pct_dissatisfied'])} dissatisfied. Highest net satisfaction: "
               f"{sat_reg['net_satisfaction'].idxmax()} ({sat_reg['net_satisfaction'].max():+.1f}); "
               f"lowest: {sat_reg['net_satisfaction'].idxmin()} "
               f"({sat_reg['net_satisfaction'].min():+.1f}).")

    # 7) Feature priority by age
    feat = analysis.option_share(df, "Q3").sort_values("share_pct", ascending=False)
    feat_age = analysis.segment_leaders(df, "Q3", "age_group")
    feat_age = feat_age[feat_age["age_group"] != "Unknown"]
    out.append(f"Top buying factor overall: {feat.iloc[0]['option']} "
               f"({_fmt_pct(feat.iloc[0]['share_pct'])}), then {feat.iloc[1]['option']} "
               f"({_fmt_pct(feat.iloc[1]['share_pct'])}). Youngest group (18-24) prioritises "
               f"{feat_age.iloc[0]['leader']}; 55+ prioritises {feat_age.iloc[-1]['leader']}.")

    # 8) Statistical tests
    for qid, by in [(pq, "region"), (pq, "age_group"), ("Q3", "age_group"), (pq, "gender")]:
        t = analysis.association_test(df, qid, by)
        strength = t["effect_size"]
        meaning = "DOES depend on" if t["significant"] else "does not clearly depend on"
        out.append(f"Chi-square test: the answer to {qid} {meaning} {by.replace('_', ' ')} "
                   f"(p = {t['p_value']:.3g}, Cramer's V = {t['cramers_v']:.2f}, {strength} effect).")
    return out


def recommendations(df):
    """Simple, data-driven business actions."""
    pq = config.PRIMARY_QUESTION
    lead = analysis.lead_analysis(df, pq)
    leaders = analysis.segment_leaders(df, pq, "region")
    weak = leaders[(leaders["leader"] != lead["leader"]) & (leaders["region"] != "Unknown")]
    feat = analysis.option_share(df, "Q3").sort_values("share_pct", ascending=False)
    sat_reg = analysis.satisfaction_score(df, "Q2", by="region")
    sat_reg = sat_reg.loc[sat_reg.index != "Unknown"]

    recs = [f"Lead marketing messages with **{feat.iloc[0]['option'].lower()}** and "
            f"**{feat.iloc[1]['option'].lower()}**, the two biggest purchase drivers."]
    if len(weak):
        recs.append(f"For {lead['leader']}: run targeted campaigns in "
                    f"{', '.join(weak['region'])}, where a competitor is preferred.")
    if not lead["significant"]:
        recs.append("The race is a statistical tie - collect a larger sample before making "
                    "big decisions.")
    recs.append(f"Investigate low satisfaction in {sat_reg['net_satisfaction'].idxmin()} "
                f"(follow-up survey or open-ended feedback).")
    recs.append("Re-run the poll monthly and watch the weekly trend chart for shifts in momentum.")
    return recs


def build_report(df, cleaning_log, chart_paths):
    """Create a Markdown report (outputs/insights_report.md)."""
    pq = config.PRIMARY_QUESTION
    summary = analysis.overall_summary(df)
    shares = analysis.option_share(df, pq)

    lines = [
        "# Poll Results - Insights Report",
        f"_Generated {datetime.now():%Y-%m-%d %H:%M} by Poll Results Visualizer_",
        "",
        "## 1. Dataset summary",
        f"- Respondents: **{summary['total_respondents']:,}**",
        f"- Responses (answers): **{summary['total_responses']:,}**",
        f"- Questions: {summary['questions']}  |  Regions: {summary['regions']}",
        f"- Polling window: {summary['start_date']} to {summary['end_date']}",
        "",
        "## 2. Data cleaning log",
        "| Step | Rows |", "|---|---:|",
        *[f"| {k.replace('_', ' ')} | {v:,} |" for k, v in cleaning_log.items()],
        "",
        f"## 3. Headline result - {config.QUESTIONS[pq]['text']}",
        "| Option | Votes | Share | 95% MoE | Rank |", "|---|---:|---:|---:|---:|",
        *[f"| {r.option} | {r.votes:,} | {r.share_pct:.1f}% | +/-{r.moe_pct:.1f} | {r.rank} |"
          for r in shares.sort_values("rank").itertuples()],
        "",
        "## 4. Key insights",
        *[f"{i}. {s}" for i, s in enumerate(generate_insights(df), start=1)],
        "",
        "## 5. Recommendations",
        *[f"- {s}" for s in recommendations(df)],
        "",
        "## 6. Charts",
        *[f"![{p.stem}](../images/{p.name})" for p in chart_paths],
        "",
        "> Note: data is synthetic and generated for portfolio/demo purposes.",
    ]
    return "\n".join(lines)
