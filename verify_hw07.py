"""Objective offline smoke checks for HW7 implementation modules."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "code"))
from hw7.bike_agent import calculator  # noqa: E402
from hw7.file_tools import confirm_bash, is_destructive  # noqa: E402


def main():
    checks = []
    checks.append({"name": "safe calculator", "pass": calculator("2*(3+4)")["success"]})
    checks.append({"name": "calculator rejects code", "pass": not calculator("__import__('os')")["success"]})
    checks.append({"name": "destructive command detected", "pass": is_destructive("rm -rf x")})
    checks.append({"name": "destructive command blocked", "pass": not confirm_bash("rm -rf x")["allowed"]})
    checks.append({"name": "safe command allowed", "pass": confirm_bash("ls")["allowed"]})
    result = {"homework": 7, "sid4": "8561", "model": "qwen3:8b", "seed": 8561, "verify_seed": 268561, "checks": checks, "pass": all(item["pass"] for item in checks)}
    output = ROOT / "reports" / "hw07" / "verification.json"; output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__": main()
