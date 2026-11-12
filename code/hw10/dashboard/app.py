from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "reports/hw10/data"

@st.cache_data
def load_json(name):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

@st.cache_data
def load_jsonl(name):
    p = DATA / name
    return pd.DataFrame([json.loads(x) for x in p.read_text().splitlines() if x.strip()]) if p.exists() else pd.DataFrame()

st.set_page_config(page_title="DATA 260 HW10", layout="wide")
st.title("DATA 260 HW10 Operations Dashboard")
page = st.sidebar.radio("Page", ["Summary", "Evaluation", "Trace lookup"])
spans = load_jsonl("spans.jsonl")
metrics = load_json("computed_metrics.json")

if page == "Summary":
    st.header("Summary")
    st.caption("Source: reports/hw10/data/*.jsonl. Time window: all records currently stored.")
    exp = load_jsonl("latency_experiment.jsonl")
    c = st.columns(4)
    c[0].metric("Requests", len(exp))
    if len(exp):
        c[1].metric("Cache hits", int(exp["cache_hit"].sum()))
        c[2].metric("Cache misses", int((~exp["cache_hit"]).sum()))
        c[3].metric("Miss p50 total (ms)", round(float(exp.loc[~exp.cache_hit, "total_ms"].median()), 2))
    st.dataframe(exp.tail(50), use_container_width=True)
elif page == "Evaluation":
    st.header("Evaluation and judge validation")
    st.json(metrics)
    st.caption("Scores are computed from raw per-case results; do not replace missing evidence with estimates.")
else:
    st.header("Trace lookup")
    examples = load_json("trace_examples.json")
    trace_id = st.text_input("trace_id", value="")
    st.caption(f"Example IDs: {examples}")
    if trace_id:
        result = spans[spans["trace_id"].astype(str) == trace_id].sort_values("start_time") if not spans.empty else spans
        if result.empty: st.warning("No span found for this trace_id.")
        else: st.dataframe(result, use_container_width=True)
