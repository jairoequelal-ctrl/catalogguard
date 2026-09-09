from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

st.set_page_config(page_title="CatalogGuard", layout="wide")
st.title("CatalogGuard — Metadata Quality & Reconciliation")
st.caption("Music publishing metadata case study")

summary_path = REPORTS / "quality_summary.csv"
if not summary_path.exists():
    st.warning("Run `python main.py` before opening the dashboard.")
    st.stop()

summary = pd.read_csv(summary_path).iloc[0]
cols = st.columns(5)
for col, key, label in zip(cols, ["catalog_quality_score", "records_processed", "exact_matches", "manual_review", "exceptions"], ["Quality Score", "Records", "Exact Matches", "Manual Review", "Exceptions"]):
    col.metric(label, summary[key])

st.subheader("Exceptions")
exceptions = pd.read_csv(REPORTS / "exceptions.csv")
severity = st.multiselect("Severity", sorted(exceptions["severity"].dropna().unique()), default=sorted(exceptions["severity"].dropna().unique()))
st.dataframe(exceptions[exceptions["severity"].isin(severity)], use_container_width=True)

st.subheader("Match Review Queue")
matches = pd.read_csv(REPORTS / "matches.csv")
st.dataframe(matches[matches["match_status"].isin(["MANUAL_REVIEW", "UNMATCHED", "UNMATCHED_EXTERNAL"])], use_container_width=True)
