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

    latency = load_json("latency_metrics.json")
    if latency:
        st.subheader("Latency p50/p95 by stage")
        stage_order = [
            "cache_lookup",
            "queue_wait_inbox_to_planner",
            "planner",
            "queue_wait_tasks_to_writer",
            "writer",
            "queue_wait_drafts_to_reviewer",
            "reviewer",
            "total",
        ]
        latency_rows = []
        for stage in stage_order:
            item = latency.get(stage, {})
            latency_rows.append({
                "stage": stage,
                "n": item.get("n"),
                "p50_ms": item.get("p50_ms"),
                "p95_ms": item.get("p95_ms"),
            })
        st.dataframe(
            pd.DataFrame(latency_rows),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Latency values are computed from the raw 50-request cache-miss "
            "experiment and span JSONL logs."
        )
elif page == "Evaluation":
    st.header("Evaluation and judge validation")
    st.json(metrics)

    part2 = load_json("part2_metrics.json")
    if part2:
        st.subheader("Part 2 stage summary")
        st.dataframe(
            pd.DataFrame([{
                "cases": part2.get("n"),
                "mean_plan_score": part2.get("mean_plan_score"),
                "mean_writer_score": part2.get("mean_writer_score"),
                "mean_final_score": part2.get("mean_final_score"),
                "mean_final_minus_draft": part2.get("mean_final_minus_draft"),
                "improved_cases": part2.get("improved_cases"),
                "unchanged_cases": part2.get("unchanged_cases"),
                "worse_cases": part2.get("worse_cases"),
            }]),
            use_container_width=True,
            hide_index=True,
        )

    stage_results = load_jsonl("evaluation_results.jsonl")
    if not stage_results.empty:
        st.subheader("Raw per-case Plan, Draft, and Final scores")
        columns = [
            "case_id",
            "trace_id",
            "plan_score",
            "writer_score",
            "final_score",
            "final_minus_draft",
        ]
        available = [c for c in columns if c in stage_results.columns]
        st.dataframe(
            stage_results[available],
            use_container_width=True,
            hide_index=True,
        )

    st.caption(
        "Scores are computed from raw per-case results. "
        "The raw file is evaluation_results.jsonl."
    )
else:
    st.header("Trace lookup")
    examples = load_json("trace_examples.json")
    trace_id = st.text_input("trace_id", value="")
    st.caption(f"Example IDs: {examples}")
    if trace_id:
        result = spans[spans["trace_id"].astype(str) == trace_id].sort_values("start_time") if not spans.empty else spans
        if result.empty: st.warning("No span found for this trace_id.")
        else: st.dataframe(result, use_container_width=True)
