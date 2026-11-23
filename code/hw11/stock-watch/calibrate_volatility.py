#!/usr/bin/env python3
"""Measure recent daily volatility for the live tickers in sources.json."""

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


def fetch_closes(base_url, ticker, user_agent):
    query = urllib.parse.urlencode({
        "range": "6mo",
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    })
    url = f"{base_url}{ticker}?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        content_type = response.headers.get("Content-Type", "")
        body = response.read().decode("utf-8", errors="replace")
    if "json" not in content_type.lower() and not body.lstrip().startswith("{"):
        raise RuntimeError(f"expected JSON but received {content_type or 'unknown content type'}")
    payload = json.loads(body)
    error = payload.get("chart", {}).get("error")
    if error:
        raise RuntimeError(str(error))
    charts = payload.get("chart", {}).get("result") or []
    if not charts:
        raise RuntimeError("response contained no chart result")
    indicators = charts[0].get("indicators", {})
    adjusted = (indicators.get("adjclose") or [{}])[0].get("adjclose")
    closes = adjusted or (indicators.get("quote") or [{}])[0].get("close") or []
    closes = [float(value) for value in closes if value is not None]
    if len(closes) < 2:
        raise RuntimeError(f"only {len(closes)} usable closes returned")
    return closes[-61:]


with open(os.path.join(HOME, "sources.json"), encoding="utf-8") as f:
    config = json.load(f)

source = next(s for s in config["sources"] if s["id"] == "volatility_calibration")
results = []
errors = []
for ticker in source["tickers"]:
    try:
        closes = fetch_closes(source["url"], ticker, config["user_agent"])
        moves = [
            (closes[i] - closes[i - 1]) / closes[i - 1] * 100
            for i in range(1, len(closes))
        ]
        abs_moves = [abs(value) for value in moves]
        results.append({
            "ticker": ticker,
            "sessions": len(moves),
            "mean_abs_daily_move_pct": round(statistics.mean(abs_moves), 3),
            "median_abs_daily_move_pct": round(statistics.median(abs_moves), 3),
            "daily_move_stddev_pct": round(statistics.stdev(moves), 3) if len(moves) > 1 else None,
            "p95_abs_daily_move_pct": round(percentile(abs_moves, 0.95), 3),
            "largest_abs_daily_move_pct": round(max(abs_moves), 3),
        })
    except Exception as exc:
        errors.append({"ticker": ticker, "error": f"{type(exc).__name__}: {exc}"})

print(json.dumps({
    "method": "Last 60 available adjusted daily close-to-close moves",
    "source": source["url"],
    "results": results,
    "errors": errors,
    "note": "Use measured values to justify or revise ticker-specific notify thresholds in policy.md.",
}, indent=2))
if errors:
    raise SystemExit(2)
