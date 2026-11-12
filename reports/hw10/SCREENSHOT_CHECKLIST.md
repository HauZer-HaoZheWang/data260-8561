# HW10 screenshot names

Capture after real data exists. Keep labels visible and save PNG files in `reports/hw10/screenshots/`.

1. `01_dashboard_summary.png` — Summary: request count, cache hit/miss, error rate, latency, data source, time window.
2. `02_dashboard_evaluation.png` — Evaluation: Planner/Writer/Reviewer scores, Spearman, MAD, repeatability.
3. `03_trace_cache_hit.png` — Trace lookup showing cache hit.
4. `04_trace_cache_miss.png` — Trace lookup showing successful Planner → Writer → Reviewer path.
5. `05_trace_failed.png` — Trace lookup showing failed stage and error.
6. `06_eval_cases_before_judge.png` — `eval_cases.json` and manually assigned `human_labels.csv` before judge results.
7. `07_latency_50_misses.png` — raw 50-request evidence and p50/p95 output, with cache_hit false visible.

Underlying JSON/CSV files must remain in the repository; screenshots are supporting evidence only.
