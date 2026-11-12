# HW10 code

Run from the repository root with the same environment used for HW8/HW9.

```bash
python verify_hw10.py
python -m code.hw10.compute_metrics
streamlit run code/hw10/dashboard/app.py
```

Before those commands:

1. Start Kafka, Redis, Ollama, and the existing Planner/Writer/Reviewer workers.
2. Run `python code/hw10/freeze_cases.py` to create 20 real Writer drafts.
3. Assign the 20 labels yourself in `reports/hw10/data/human_labels.csv`.
4. Commit `eval_cases.json` and `human_labels.csv` before running `python code/hw10/evaluate.py`.
5. Run `python code/hw10/latency_experiment.py` for 50 intentionally unique cache misses.

The same `correlation_id` is carried through the Kafka messages and is written as `trace_id` in every span. The code does not create a second request ID.
