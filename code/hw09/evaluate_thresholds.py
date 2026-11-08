import json
import math
import time
from pathlib import Path
from collections import Counter

import requests

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "code/hw09/cache_cases.yaml"
OUT = ROOT / "reports/hw09"
MODEL = "nomic-embed-text"

# Explicit assumptions, not real API billing.
COST_PER_HIT_USD = 0.00001
COST_PER_MISS_USD = 0.002


def load_cases(path):
    # Parse the restricted YAML structure generated in Step 3.1.
    seeds = []
    cases = []
    thresholds = []
    section = None
    current = None

    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "seeds:":
            section = "seeds"
            continue
        if line == "cases:":
            section = "cases"
            continue
        if line.startswith("thresholds:"):
            thresholds = json.loads(line.split(":", 1)[1].strip())
            continue
        if line.startswith("- id:"):
            current = {"id": line.split(":", 1)[1].strip()}
            (seeds if section == "seeds" else cases).append(current)
            continue
        if current is not None and ":" in line:
            key, value = line.split(":", 1)
            value = value.strip()
            if value in ("true", "false"):
                current[key] = value == "true"
            elif value.startswith('"'):
                current[key] = json.loads(value)
            else:
                current[key] = value

    return seeds, cases, thresholds


def embed(session, question):
    response = session.post(
        "http://localhost:11434/api/embed",
        json={"model": MODEL, "input": question},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b)


def main():
    print("Student: Haozhe Wang", flush=True)
    print("DATA 260 HW9 - Part 3 Threshold Sweep", flush=True)

    seeds, cases, thresholds = load_cases(SOURCE)

    assert len(seeds) == 10
    assert len(cases) == 40
    assert len(thresholds) == 5
    assert Counter(c["category"] for c in cases) == {
        "exact": 10,
        "paraphrase": 10,
        "hard_negative": 10,
        "unrelated": 10,
    }

    print("PASS: Loaded 40 precommitted cases", flush=True)
    print("Thresholds:", thresholds, flush=True)

    session = requests.Session()
    vectors = {}

    all_questions = list(dict.fromkeys(
        [s["question"] for s in seeds] +
        [c["question"] for c in cases]
    ))

    print(f"Embedding {len(all_questions)} unique questions...", flush=True)

    for index, question in enumerate(all_questions, 1):
        started = time.perf_counter()
        vectors[question] = embed(session, question)
        elapsed = (time.perf_counter() - started) * 1000
        print(
            f"Embedding {index}/{len(all_questions)} "
            f"latency_ms={elapsed:.2f}",
            flush=True
        )

    seed_lookup = {s["id"]: s for s in seeds}
    detailed = []

    for case in cases:
        matches = [
            (cosine(vectors[case["question"]],
                    vectors[seed["question"]]), seed)
            for seed in seeds
        ]

        similarity, nearest_seed = max(matches, key=lambda x: x[0])

        detailed.append({
            **case,
            "nearest_seed": nearest_seed["id"],
            "nearest_question": nearest_seed["question"],
            "similarity": round(similarity, 6),
        })

    benchmark = json.loads(
        (OUT / "part2_summary.json").read_text()
    )

    hit_ms = benchmark["avg_hit_latency_ms"]
    miss_ms = benchmark["avg_miss_latency_ms"]

    summary = []
    false_examples = []

    print("\n===== THRESHOLD SWEEP =====", flush=True)

    for threshold in thresholds:
        hits = 0
        false_hits = 0
        wrong_seed_hits = 0
        false_misses = 0
        threshold_details = []

        for case in detailed:
            predicted_hit = case["similarity"] >= threshold
            expected_hit = case["expected_hit"]

            # A positive hit to the wrong seed is also incorrect.
            wrong_seed = (
                predicted_hit
                and expected_hit
                and case["nearest_seed"] != case["target_seed"]
            )

            is_false_hit = (
                predicted_hit and
                (not expected_hit or wrong_seed)
            )

            if predicted_hit:
                hits += 1
            if is_false_hit:
                false_hits += 1
            if wrong_seed:
                wrong_seed_hits += 1
            if expected_hit and not predicted_hit:
                false_misses += 1

            row = {
                **case,
                "threshold": threshold,
                "predicted_hit": predicted_hit,
                "false_hit": is_false_hit,
                "wrong_seed_hit": wrong_seed,
            }
            threshold_details.append(row)

            if is_false_hit:
                false_examples.append(row)

        misses = 40 - hits
        negative_count = sum(
            not c["expected_hit"] for c in detailed
        )
        negative_false_hits = sum(
            r["predicted_hit"] and not r["expected_hit"]
            for r in threshold_details
        )

        estimated_avg_latency_ms = (
            hits * hit_ms + misses * miss_ms
        ) / 40

        estimated_cost_usd = (
            hits * COST_PER_HIT_USD +
            misses * COST_PER_MISS_USD
        )

        item = {
            "threshold": threshold,
            "hits": hits,
            "misses": misses,
            "hit_rate_percent": round(hits / 40 * 100, 2),
            "false_hits": false_hits,
            "negative_false_hit_rate_percent": round(
                negative_false_hits / negative_count * 100, 2
            ),
            "wrong_seed_hits": wrong_seed_hits,
            "false_misses": false_misses,
            "estimated_avg_latency_ms": round(
                estimated_avg_latency_ms, 2
            ),
            "estimated_total_cost_usd": round(
                estimated_cost_usd, 6
            ),
        }
        summary.append(item)

        print(
            f"threshold={threshold:.2f} "
            f"hit_rate={item['hit_rate_percent']:.1f}% "
            f"false_hits={false_hits} "
            f"negative_false_hit_rate="
            f"{item['negative_false_hit_rate_percent']:.1f}% "
            f"false_misses={false_misses} "
            f"estimated_latency_ms="
            f"{item['estimated_avg_latency_ms']:.2f} "
            f"estimated_cost_usd="
            f"{item['estimated_total_cost_usd']:.6f}",
            flush=True
        )

    result = {
        "student": "Haozhe Wang",
        "model": MODEL,
        "method": "Offline cosine similarity sweep with real Ollama embeddings",
        "precommitted_dataset": "code/hw09/cache_cases.yaml",
        "measurement_note": (
            "Hit decisions use actual embedding cosine similarities. "
            "Latency is modeled using Part 2 measured averages; "
            "cost is a hypothetical per-request model, not billing."
        ),
        "cost_model": {
            "cost_per_hit_usd": COST_PER_HIT_USD,
            "cost_per_miss_usd": COST_PER_MISS_USD,
        },
        "threshold_summary": summary,
        "cases": detailed,
        "false_hit_examples": false_examples,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "part3_threshold_results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False)
    )

    with (OUT / "part3_threshold_table.csv").open("w") as f:
        f.write(
            "threshold,hits,misses,hit_rate_percent,"
            "false_hits,negative_false_hit_rate_percent,"
            "wrong_seed_hits,false_misses,"
            "estimated_avg_latency_ms,estimated_total_cost_usd\n"
        )
        for r in summary:
            f.write(",".join(str(r[k]) for k in [
                "threshold", "hits", "misses",
                "hit_rate_percent", "false_hits",
                "negative_false_hit_rate_percent",
                "wrong_seed_hits", "false_misses",
                "estimated_avg_latency_ms",
                "estimated_total_cost_usd"
            ]) + "\n")

    print("\n===== FALSE HIT EXAMPLE =====")
    if false_examples:
        example = false_examples[0]
        print(json.dumps(
            example, indent=2, ensure_ascii=False
        ))
    else:
        print("No false hit observed at these thresholds.")

    print("\nPASS: Evaluated 40 cases at 5 thresholds")
    print("PASS: Results saved to reports/hw09/")
    print("=== PART 3 THRESHOLD SWEEP COMPLETE ===")


if __name__ == "__main__":
    main()
