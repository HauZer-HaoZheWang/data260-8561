import json
from collections import Counter

RUNS = "reports/hw01/raw/nondeterminism_runs.json"
data = json.load(open(RUNS))


def pct(sorted_vals, p):
    if not sorted_vals:
        return 0
    k = (len(sorted_vals) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo))


for temp in [0.7, 0.0]:
    rows = [r for r in data if r["temperature"] == temp and r["tags"]]
    sets = [tuple(sorted(r["tags"])) for r in rows]
    tag_counts = Counter(t for s in sets for t in set(s))
    lat = sorted(r["latency_ms"] for r in rows)

    print(f"\n=== temperature = {temp}  (n={len(rows)}) ===")
    print("Distinct tag sets      :", len(set(sets)))
    print("Tags in ALL runs       :", [t for t, c in tag_counts.items() if c == len(rows)])
    print("Tags in EXACTLY 1 run  :", [t for t, c in tag_counts.items() if c == 1])
    print(f"Latency p50/p95/p99 ms : {pct(lat,50)} / {pct(lat,95)} / {pct(lat,99)}")
    print("Unique sets detail:")
    for s, c in Counter(sets).most_common():
        print(f"  {c}x  {list(s)}")
