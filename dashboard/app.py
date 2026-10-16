"""
Interactive Streamlit dashboard for the Poll Results Visualizer.

Run from the project root:
    streamlit run dashboard/app.py

Features
- Uses the cleaned dataset (or lets you upload your own CSV / Google Form export)
- Sidebar filters: question, region, age group, gender, date range
- KPI tiles, vote-share bar + donut, segment comparison, weekly trend
- Auto-generated insights and a downloadable filtered dataset
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))  # make `src` importable

from src import analysis, config  # noqa: E402
from src.data_cleaning import clean_poll_data  # noqa: E402
from src.data_generator import generate_poll_data  # noqa: E402
from src.data_loader import is_long_format, wide_to_long  # noqa: E402
from src.visualization import CATEGORICAL, LIKERT_COLORS  # noqa: E402

st.set_page_config(page_title="Poll Results Visualizer", page_icon="📊", layout="wide")


# ---------------------------------------------------------------------------
# Data loading (cached so filters are instant)
# ---------------------------------------------------------------------------
@st.cache_data
def load_default():
    if config.CLEAN_DATA_FILE.exists():
        df = pd.read_csv(config.CLEAN_DATA_FILE, parse_dates=["response_date"])
        return df
    df, _ = clean_poll_data(generate_poll_data(), verbose=False)
    return df


@st.cache_data
def load_uploaded(file):
    raw = pd.read_csv(file)
    if not is_long_format(raw):
        raw = wide_to_long(raw)
    df, _ = clean_poll_data(raw, verbose=False)
    return df


def color_map(qid, options):
    if config.QUESTIONS.get(qid, {}).get("type") == "likert":
        return {o: LIKERT_COLORS.get(o, "#898781") for o in options}
    known = config.QUESTIONS.get(qid, {}).get("options", list(options))
    return {o: CATEGORICAL[known.index(o) % 8] if o in known else "#898781" for o in options}


st.sidebar.title("📊 Poll Results Visualizer")
upload = st.sidebar.file_uploader("Upload poll CSV (optional)", type="csv",
                                  help="Long format or a Google Forms export")
data = load_uploaded(upload) if upload else load_default()

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
questions = data[["question_id", "question"]].drop_duplicates().sort_values("question_id")
q_label = st.sidebar.selectbox("Question", questions["question_id"] + " - " + questions["question"])
qid = q_label.split(" - ")[0]


def multiselect(label, col):
    values = sorted(data[col].dropna().unique())
    return st.sidebar.multiselect(label, values, default=values)


regions = multiselect("Region", "region")
ages = multiselect("Age group", "age_group")
genders = multiselect("Gender", "gender")
dmin, dmax = data["response_date"].min().date(), data["response_date"].max().date()
dates = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
segment_by = st.sidebar.radio("Compare by", ["region", "age_group", "gender"],
                              format_func=lambda s: s.replace("_", " ").title())

mask = (data["region"].isin(regions) & data["age_group"].isin(ages)
        & data["gender"].isin(genders))
if isinstance(dates, tuple) and len(dates) == 2:
    mask &= data["response_date"].dt.date.between(dates[0], dates[1])
df = data[mask]

if df[df["question_id"] == qid].empty:
    st.warning("No responses match these filters. Widen the filters in the sidebar.")
    st.stop()

# ---------------------------------------------------------------------------
# Header + KPIs
# ---------------------------------------------------------------------------
st.title(questions.set_index("question_id").loc[qid, "question"])
st.caption("Synthetic demo data" if upload is None else f"Uploaded file: {upload.name}")

lead = analysis.lead_analysis(df, qid)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Respondents", f"{df['respondent_id'].nunique():,}")
k2.metric("Leading option", lead["leader"], f"{lead['leader_share']:.1f}% share")
k3.metric("Lead over #2", f"{lead['lead_pct_points']:.1f} pts",
          "significant" if lead["significant"] else "statistical tie",
          delta_color="normal" if lead["significant"] else "off")
if "Q2" in df["question_id"].unique():
    k4.metric("Avg satisfaction", f"{analysis.satisfaction_score(df, 'Q2')['avg_score']:.2f} / 5")

# ---------------------------------------------------------------------------
# Overall share: bar + donut
# ---------------------------------------------------------------------------
shares = analysis.option_share(df, qid)
cmap = color_map(qid, shares["option"])
c1, c2 = st.columns([3, 2])
with c1:
    fig = px.bar(shares.sort_values("share_pct"), x="share_pct", y="option", orientation="h",
                 error_x="moe_pct", color="option", color_discrete_map=cmap,
                 text=shares.sort_values("share_pct")["share_pct"].map("{:.1f}%".format),
                 labels={"share_pct": "Share of responses (%)", "option": ""},
                 hover_data={"votes": True, "moe_pct": ":.1f"},
                 title="Vote share with 95% margin of error")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False, height=380, margin=dict(r=60))
    st.plotly_chart(fig, width="stretch")
with c2:
    fig = px.pie(shares, names="option", values="votes", hole=0.55, color="option",
                 color_discrete_map=cmap, title="Share of votes")
    fig.update_traces(textinfo="label+percent", marker_line_color="white", marker_line_width=2)
    fig.update_layout(showlegend=False, height=380)
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Segment comparison
# ---------------------------------------------------------------------------
seg = analysis.segment_share(df, qid, segment_by).reset_index().melt(
    id_vars=segment_by, var_name="option", value_name="share_pct")
fig = px.bar(seg, x="share_pct", y=segment_by, color="option", orientation="h",
             color_discrete_map=cmap, text=seg["share_pct"].map("{:.0f}%".format),
             title=f"Answer mix by {segment_by.replace('_', ' ')} (100% stacked)",
             labels={"share_pct": "% of segment", segment_by: ""})
fig.update_layout(barmode="stack", height=420, legend_title_text="")
fig.update_traces(marker_line_color="white", marker_line_width=1.5)
st.plotly_chart(fig, width="stretch")

c3, c4 = st.columns(2)
with c3:
    trend = analysis.trend_share(df, qid).reset_index().melt(
        id_vars="period_start", var_name="option", value_name="share_pct")
    fig = px.line(trend, x="period_start", y="share_pct", color="option", markers=True,
                  color_discrete_map=cmap, title="Weekly trend",
                  labels={"period_start": "Week", "share_pct": "Share (%)"})
    fig.update_layout(hovermode="x unified", height=380, legend_title_text="")
    st.plotly_chart(fig, width="stretch")
with c4:
    leaders = analysis.segment_leaders(df, qid, segment_by)
    st.subheader(f"Winner in each {segment_by.replace('_', ' ')}")
    st.dataframe(leaders, width="stretch", hide_index=True)
    test = analysis.association_test(df, qid, segment_by)
    st.info(f"Chi-square test: p = {test['p_value']:.3g}, Cramer's V = {test['cramers_v']:.2f} "
            f"-> answers {'**do**' if test['significant'] else 'do **not** clearly'} differ "
            f"by {segment_by.replace('_', ' ')}.")

# ---------------------------------------------------------------------------
# Tables + download
# ---------------------------------------------------------------------------
with st.expander("Vote/share summary table"):
    st.dataframe(shares, width="stretch", hide_index=True)
with st.expander("Filtered raw responses"):
    st.dataframe(df.head(500), width="stretch", hide_index=True)
st.download_button("⬇️ Download filtered data (CSV)", df.to_csv(index=False).encode(),
                   "filtered_poll_data.csv", "text/csv")
