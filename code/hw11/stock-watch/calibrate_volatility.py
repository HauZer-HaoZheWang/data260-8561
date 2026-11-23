#!/usr/bin/env python3
"""Measure recent daily volatility for the live tickers in sources.json."""

import csv
import io
import json
import math
import os
import statistics
import urllib.parse
import urllib.request


HOME = os.path.dirname(os.path.abspath(__file__))


def percentile(values, pct):
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * pct
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


with open(os.path.join(HOME, "sources.json"), encoding="utf-8") as f:
    config = json.load(f)

source = next(s for s in config["sources"] if s["id"] == "prices_live")
results = []
for ticker in source["tickers"]:
    url = source["url"] + "?" + urllib.parse.urlencode({"s": ticker, "i": "d"})
    request = urllib.request.Request(url, headers={"User-Agent": config["user_agent"]})
    with urllib.request.urlopen(request, timeout=30) as response:
        text = response.read().decode("utf-8", errors="replace")
    rows = [
        row for row in csv.DictReader(io.StringIO(text))
        if row.get("Close") not in (None, "", "N/D")
    ][-61:]
    closes = [float(row["Close"]) for row in rows]
    moves = [(closes[i] - closes[i - 1]) / closes[i - 1] * 100 for i in range(1, len(closes))]
    abs_moves = [abs(x) for x in moves]
    results.append({
        "ticker": ticker.split(".")[0].upper(),
        "sessions": len(moves),
        "mean_abs_daily_move_pct": round(statistics.mean(abs_moves), 3),
        "median_abs_daily_move_pct": round(statistics.median(abs_moves), 3),
        "daily_move_stddev_pct": round(statistics.stdev(moves), 3) if len(moves) > 1 else None,
        "p95_abs_daily_move_pct": round(percentile(abs_moves, 0.95), 3),
        "largest_abs_daily_move_pct": round(max(abs_moves), 3),
    })

print(json.dumps({
    "method": "Last 60 available daily close-to-close moves from Stooq",
    "results": results,
    "note": "Use these measured values to justify or revise the ticker-specific notify thresholds in policy.md."
}, indent=2))
