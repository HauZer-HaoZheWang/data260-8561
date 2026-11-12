# DATA 260 Homework 10

Use 14 pt bold main headings, 12 pt bold subheadings, 11 pt body text, labeled screenshots, and no more than 35 pages.

## 0. Configuration and repository
State PREFIX, ports, local Ollama model, and run date.

## 1. Streamlit dashboard
Insert screenshots 01–05. State the source and time window for every metric.

## 2. Automated evaluation
Explain GEval criteria, local Ollama judge, timeout, malformed-message handling, and conversion `judge_1_to_5 = 1 + 4 * geval_0_to_1`.

## 3. Judge validation
Report raw per-case data, Spearman, MAD, score-change rate, mean absolute change, and maximum absolute change. State whether the judge is safe for deployment gating.

## 4. Tracing and latency
Explain that `correlation_id` is reused as `trace_id`. Include cache-hit, successful cache-miss, and failed trace IDs. Include the required p50/p95 table and identify the first optimization.

## 5. Honest conclusion
If final did not improve over draft, report that directly.

## AI use statement
I used ChatGPT to explain concepts, organize code, and review wording. I ran and inspected the final code and experiments. Human labels were assigned by me before judge results were generated.
