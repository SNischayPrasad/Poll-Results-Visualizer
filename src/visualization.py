"""
visualization.py
----------------
Static, report-ready charts (PNG) built with Matplotlib + Seaborn.

Design rules used for every chart (worth mentioning in interviews):
- Each OPTION always keeps the same colour in every chart (colour = identity).
- The Likert (satisfaction) scale uses a diverging blue <-> red palette with a
  grey "Neutral" midpoint, because it has a direction (good vs bad).
- Light gridlines, no top/right borders, values labelled directly on bars,
  so the chart can be read without guessing from the axis.
- One y-axis per chart (no dual-axis charts).
"""

import matplotlib

matplotlib.use("Agg")  # render to files, no window needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import seaborn as sns

from src import analysis, config

# ---------------------------------------------------------------------------
# Palette (colour-blind-checked categorical order) and chart ink colours
# ---------------------------------------------------------------------------
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
               "#008300", "#4a3aa7", "#e34948"]
LIKERT_COLORS = {
    "Very Satisfied": "#1c5cab", "Satisfied": "#6da7ec", "Neutral": "#c9c8c2",
    "Dissatisfied": "#f19a99", "Very Dissatisfied": "#c8302f",
}
SURFACE, INK, INK_2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK_2, "axes.titlecolor": INK,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.titlepad": 12, "axes.labelsize": 10,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"], "font.size": 10,
    "legend.frameon": False,
})


def option_colors(qid):
    """Fixed option -> colour mapping for a question."""
    options = config.QUESTIONS[qid]["options"]
    if config.QUESTIONS[qid]["type"] == "likert":
        return {o: LIKERT_COLORS[o] for o in options}
    return {o: CATEGORICAL[i % len(CATEGORICAL)] for i, o in enumerate(options)}


def _save(fig, name):
    config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    path = config.IMAGES_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _spread(values, min_gap):
    """Nudge end-of-line label positions apart so labels never overlap."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    pos = list(values)
    for a, b in zip(order, order[1:]):
        if pos[b] - pos[a] < min_gap:
            pos[b] = pos[a] + min_gap
    return pos


def _subtitle(ax, text):
    ax.text(0, 1.01, text, transform=ax.transAxes, color=INK_2, fontsize=9, va="bottom")


# ---------------------------------------------------------------------------
# 1) Bar chart: overall share with 95% margin of error
# ---------------------------------------------------------------------------
def plot_option_share_bar(df, qid):
    shares = analysis.option_share(df, qid).sort_values("share_pct")
    colors = option_colors(qid)
    n = int(shares["votes"].sum())

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.barh(shares["option"], shares["share_pct"], height=0.55,
            color=[colors[o] for o in shares["option"]],
            xerr=shares["moe_pct"], error_kw=dict(ecolor=INK_2, lw=1, capsize=3))
    for y, (pct, moe) in enumerate(zip(shares["share_pct"], shares["moe_pct"])):
        ax.text(pct + moe + 0.6, y, f"{pct:.1f}%", va="center", color=INK, fontsize=10)
    ax.set_title(config.QUESTIONS[qid]["text"], pad=22)
    _subtitle(ax, f"Share of responses (n = {n:,}); whiskers = 95% margin of error")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_xlim(0, shares["ci_high_pct"].max() * 1.18)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", colors=INK, labelsize=10, length=0)
    return _save(fig, f"bar_{qid.lower()}_share.png")


# ---------------------------------------------------------------------------
# 2) Pie (donut) chart: vote share of the primary question
# ---------------------------------------------------------------------------
def plot_option_share_pie(df, qid):
    shares = analysis.option_share(df, qid)
    colors = option_colors(qid)
    lead = analysis.lead_analysis(df, qid)

    fig, ax = plt.subplots(figsize=(6.2, 6.2))
    wedges, _ = ax.pie(
        shares["votes"], colors=[colors[o] for o in shares["option"]], startangle=90,
        counterclock=False, wedgeprops=dict(width=0.38, edgecolor=SURFACE, linewidth=2))
    # Label every slice from outside: option + share
    for w, opt, pct in zip(wedges, shares["option"], shares["share_pct"]):

        ang = np.deg2rad((w.theta2 + w.theta1) / 2)
        x, y = np.cos(ang), np.sin(ang)
        ax.annotate(f"{opt}\n{pct:.1f}%", xy=(0.81 * x, 0.81 * y), xytext=(1.22 * x, 1.18 * y),
                    ha="center", va="center", fontsize=10, color=INK,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.text(0, 0.08, lead["leader"], ha="center", fontsize=18, fontweight="bold", color=INK)
    ax.text(0, -0.12, f"leads with {lead['leader_share']:.1f}%", ha="center",
            fontsize=10, color=INK_2)
    ax.set_title(f"Vote share - {config.QUESTIONS[qid]['text']}", loc="center", pad=34)
    ax.axis("equal")
    return _save(fig, f"pie_{qid.lower()}_share.png")


# ---------------------------------------------------------------------------
# 3) 100% stacked bar: option share inside each segment (region, age, ...)
# ---------------------------------------------------------------------------
def plot_segment_stacked(df, qid, by, label):
    table = analysis.segment_share(df, qid, by)
    table = table.loc[table.index != "Unknown"]
    colors = option_colors(qid)

    fig, ax = plt.subplots(figsize=(9, 0.62 * len(table) + 1.9))
    left = [0.0] * len(table)
    for opt in table.columns:
        vals = table[opt].values
        ax.barh(table.index, vals, left=left, height=0.62, color=colors[opt],
                edgecolor=SURFACE, linewidth=2, label=opt)
        for i, v in enumerate(vals):  # label only segments wide enough to read
            if v >= 9:
                txt_color = INK if opt in ("Neutral", "Satisfied", "Dissatisfied") else "white"
                ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center",
                        fontsize=9, color=txt_color)
        left = [l + v for l, v in zip(left, vals)]
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title(f"{config.QUESTIONS[qid]['text']} - by {label}", pad=30)
    ax.legend(ncol=len(table.columns), loc="lower left", bbox_to_anchor=(0, 1.0),
              fontsize=9, handlelength=1, handleheight=1)
    ax.grid(False)
    ax.tick_params(axis="y", colors=INK, length=0)
    return _save(fig, f"stacked_{qid.lower()}_by_{by}.png")


# ---------------------------------------------------------------------------
# 4) Heatmap: demographic comparison at a glance
# ---------------------------------------------------------------------------
def plot_segment_heatmap(df, qid, by, label):
    table = analysis.segment_share(df, qid, by)
    table = table.loc[table.index != "Unknown"]
    fig, ax = plt.subplots(figsize=(8, 0.55 * len(table) + 1.8))
    sns.heatmap(table, annot=True, fmt=".1f", cmap="Blues", linewidths=2,
                linecolor=SURFACE, cbar_kws={"label": "% of segment", "shrink": 0.8},
                annot_kws={"fontsize": 9}, ax=ax)
    ax.set_title(f"{config.QUESTIONS[qid]['text']} - % by {label}")
    ax.set_xlabel("")
    ax.set_ylabel(label)
    ax.tick_params(colors=INK, length=0)
    return _save(fig, f"heatmap_{qid.lower()}_by_{by}.png")


# ---------------------------------------------------------------------------
# 5) Trend chart: weekly share over the polling window
# ---------------------------------------------------------------------------
def plot_trend(df, qid):
    trend = analysis.trend_share(df, qid)
    colors = option_colors(qid)

    fig, ax = plt.subplots(figsize=(9, 4.6))
    label_y = _spread(list(trend.iloc[-1]), min_gap=trend.max().max() * 0.05)
    for opt, y in zip(trend.columns, label_y):
        ax.plot(trend.index, trend[opt], color=colors[opt], lw=2, marker="o",
                markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.5, label=opt)
        # direct label at the end of each line
        ax.text(trend.index[-1], y, f"  {opt} {trend[opt].iloc[-1]:.0f}%",
                va="center", fontsize=9, color=INK_2)
    ax.set_title(f"Weekly trend - {config.QUESTIONS[qid]['text']}", pad=22)
    _subtitle(ax, "Share of responses per week (week starting Monday)")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_ylim(0, trend.max().max() * 1.2)
    ax.legend(loc="upper left", ncol=len(trend.columns), fontsize=9)
    ax.grid(axis="x", visible=False)
    fig.autofmt_xdate()
    ax.margins(x=0.02)
    fig.subplots_adjust(right=0.82)
    return _save(fig, f"trend_{qid.lower()}_weekly.png")


# ---------------------------------------------------------------------------
# 6) Satisfaction score by region (sorted bar with average line)
# ---------------------------------------------------------------------------
def plot_satisfaction_by(df, by, label, qid="Q2"):
    sat = analysis.satisfaction_score(df, qid, by=by)
    sat = sat.loc[sat.index != "Unknown"].sort_values("net_satisfaction")
    overall = analysis.satisfaction_score(df, qid)
    overall_net = overall["pct_satisfied"] - overall["pct_dissatisfied"]

    fig, ax = plt.subplots(figsize=(8, 0.55 * len(sat) + 1.8))
    ax.barh(sat.index, sat["net_satisfaction"], height=0.55, color="#2a78d6")
    ax.axvline(overall_net, color=INK_2, lw=1, ls="--")
    ax.text(overall_net, len(sat) - 0.35, f" overall {overall_net:.1f}", color=INK_2, fontsize=9)
    for y, v in enumerate(sat["net_satisfaction"]):
        ax.text(v + 0.5, y, f"{v:.1f}", va="center", fontsize=9)
    ax.set_title(f"Net satisfaction by {label}", pad=22)
    _subtitle(ax, "% (Very) Satisfied minus % (Very) Dissatisfied")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", colors=INK, length=0)
    return _save(fig, f"net_satisfaction_by_{by}.png")


# ---------------------------------------------------------------------------
# 7) One-page static dashboard (good for README / LinkedIn screenshot)
# ---------------------------------------------------------------------------
def plot_dashboard(df, qid=config.PRIMARY_QUESTION):
    summary = analysis.overall_summary(df)
    lead = analysis.lead_analysis(df, qid)
    sat = analysis.satisfaction_score(df, "Q2")
    shares = analysis.option_share(df, qid)
    colors = option_colors(qid)
    region = analysis.segment_share(df, qid, "region")
    region = region.loc[region.index != "Unknown"]
    trend = analysis.trend_share(df, qid)
    feature = analysis.option_share(df, "Q3").sort_values("share_pct")

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, height_ratios=[0.42, 1, 1], hspace=0.55, wspace=0.32)
    fig.suptitle("Poll Results Dashboard - Smartphone Consumer Poll", x=0.125, ha="left",
                 fontsize=18, fontweight="bold", y=0.98)
    fig.text(0.125, 0.935, f"{summary['start_date']} to {summary['end_date']}  |  "
             f"{summary['total_respondents']:,} respondents  |  synthetic data",
             color=INK_2, fontsize=10)

    # KPI tiles
    kpis = [("Respondents", f"{summary['total_respondents']:,}"),
            ("Leading brand", f"{lead['leader']} {lead['leader_share']:.1f}%"),
            ("Lead over #2", f"+{lead['lead_pct_points']:.1f} pts"
             + (" (sig.)" if lead["significant"] else " (tie)")),
            ("Avg satisfaction", f"{sat['avg_score']:.2f} / 5")]
    kpi_gs = gs[0, :].subgridspec(1, 4, wspace=0.08)
    for i, (title, value) in enumerate(kpis):
        ax = fig.add_subplot(kpi_gs[0, i])
        ax.set_facecolor("#f3f2ee")
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.text(0.06, 0.68, title, fontsize=10, color=INK_2, transform=ax.transAxes)
        ax.text(0.06, 0.22, value, fontsize=19, fontweight="bold", transform=ax.transAxes)

    # Bar - overall share
    ax = fig.add_subplot(gs[1, 0])
    s = shares.sort_values("share_pct")
    ax.barh(s["option"], s["share_pct"], color=[colors[o] for o in s["option"]], height=0.55)
    for y, v in enumerate(s["share_pct"]):
        ax.text(v + 0.5, y, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_title("Next-brand preference")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.grid(axis="y", visible=False); ax.tick_params(axis="y", length=0, colors=INK)

    # Stacked - by region
    ax = fig.add_subplot(gs[1, 1:])
    left = [0.0] * len(region)
    for opt in region.columns:
        ax.barh(region.index, region[opt], left=left, color=colors[opt], height=0.6,
                edgecolor=SURFACE, linewidth=2, label=opt)
        for i, v in enumerate(region[opt]):
            if v >= 10:
                ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center",
                        fontsize=8.5, color="white")
        left = [l + v for l, v in zip(left, region[opt])]
    ax.invert_yaxis(); ax.set_xlim(0, 100); ax.grid(False)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title("Brand preference by region", pad=26)
    ax.legend(ncol=5, loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=9)
    ax.tick_params(axis="y", length=0, colors=INK)

    # Trend
    ax = fig.add_subplot(gs[2, :2])
    label_y = _spread(list(trend.iloc[-1]), min_gap=trend.max().max() * 0.07)
    for opt, y in zip(trend.columns, label_y):
        ax.plot(trend.index, trend[opt], color=colors[opt], lw=2, marker="o", markersize=4,
                label=opt)
        ax.text(trend.index[-1], y, f"  {opt}", va="center", fontsize=8.5, color=INK_2)
    ax.set_title("Weekly trend of brand preference")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", labelrotation=20)

    # Feature priorities
    ax = fig.add_subplot(gs[2, 2])
    ax.barh(feature["option"], feature["share_pct"], color="#2a78d6", height=0.55)
    for y, v in enumerate(feature["share_pct"]):
        ax.text(v + 0.5, y, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_title("Most important feature")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.grid(axis="y", visible=False); ax.tick_params(axis="y", length=0, colors=INK)

    return _save(fig, "dashboard_summary.png")


def create_all_charts(df):
    """Generate every chart and return the list of saved file paths."""
    pq = config.PRIMARY_QUESTION
    paths = [
        plot_option_share_bar(df, pq),
        plot_option_share_bar(df, "Q3"),
        plot_option_share_pie(df, pq),
        plot_segment_stacked(df, pq, "region", "region"),
        plot_segment_stacked(df, pq, "age_group", "age group"),
        plot_segment_stacked(df, "Q2", "region", "region"),
        plot_segment_heatmap(df, pq, "age_group", "Age group"),
        plot_segment_heatmap(df, "Q3", "age_group", "Age group"),
        plot_trend(df, pq),
        plot_satisfaction_by(df, "region", "region"),
        plot_satisfaction_by(df, "age_group", "age group"),
        plot_dashboard(df),
    ]
    return paths
