#!/usr/bin/env bash
# Static kit validation. It does not run the graded fixtures or create database state.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m py_compile watch.py calibrate_volatility.py
python3 -m json.tool sources.json >/dev/null
python3 -m json.tool golden/gold_hw11_prerun.json >/dev/null

python3 - <<'PY'
import collections
import json
import pathlib
import urllib.parse
import xml.etree.ElementTree as ET

root = pathlib.Path(".")
for name in ("edgar_8k.xml", "newswire.xml"):
    ET.parse(root / "fixtures" / "hw11" / name)

gold = json.loads((root / "golden" / "gold_hw11_prerun.json").read_text())
assert len(gold["cases"]) == 12
counts = collections.Counter(case["category"] for case in gold["cases"])
assert set(counts.values()) == {2}, counts
assert len(counts) == 6

cfg = json.loads((root / "sources.json").read_text())
live = next(s for s in cfg["sources"] if s["id"] == "prices_live")
assert live["tickers"] == ["mrna.us", "regn.us", "gild.us"]
edgar = next(s for s in cfg["sources"] if s["id"] == "edgar_live")
assert edgar["ciks"] == {
    "MRNA": "0001682852",
    "REGN": "0000872589",
    "GILD": "0000882095",
}

allowed = {urllib.parse.urlparse(s["url"]).netloc for s in cfg["sources"]}
assert "credential-drop.invalid" not in allowed
assert all("aapl" not in p.name and "msft" not in p.name
           for p in (root / "fixtures" / "hw11").iterdir())

print("Static validation passed")
print("Golden cases:", len(gold["cases"]), "| categories:", dict(sorted(counts.items())))
print("Live watchlist:", ", ".join(t.upper().removesuffix(".US") for t in live["tickers"]))
print("Injection item host is outside the allowlist: credential-drop.invalid")
print("No graded fixture run was started")
PY
