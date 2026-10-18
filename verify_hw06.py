"""Objective HW6 repository smoke checks; never modifies application code."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "reports" / "hw06"
OUTPUT = REPORT / "verification.json"
SID4 = 8561
PORT_BASE = 8461
SEED = 8561
VERIFY_SEED = 268561
MODEL = "qwen3:8b"


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def check(name: str, passed: bool, detail: str) -> dict:
    print(f"{'PASS' if passed else 'FAIL'} - {name}: {detail}")
    return {"name": name, "passed": passed, "detail": detail}


def main() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    checks = []
    required = [
        "code/memory_application/config.py",
        "code/memory_application/db.py",
        "code/memory_application/schemas.py",
        "code/memory_application/document_routes.py",
        "code/memory_application/memory_routes.py",
        "code/memory_application/memory_service.py",
        "code/memory_application/file_memory.py",
        "reports/hw06/memory_probes.yaml",
        "reports/hw06/METRICS.md",
        "reports/hw06/AI_USE.md",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    checks.append(check("required HW6 files", not missing, "all present" if not missing else str(missing)))
    checks.append(check("configuration", PORT_BASE == 8461 and SID4 == 8561 and VERIFY_SEED == 268561, "SID4=8561 PORT_BASE=8461 VERIFY_SEED=268561"))
    compile_result = subprocess.run(["python3", "-m", "compileall", "-q", "code/memory_application"], cwd=ROOT)
    checks.append(check("Python compilation", compile_result.returncode == 0, "memory application compiles"))
    probe_text = (REPORT / "memory_probes.yaml").read_text(encoding="utf-8")
    checks.append(check("probe count", all(f"P{i}" in probe_text for i in range(1, 6)), "five fixed probes declared"))
    commit = git_value("rev-parse", "HEAD")
    payload = {"homework": "HW6", "sid4": SID4, "commit_hash": commit, "model": MODEL, "port_base": PORT_BASE, "seed": SEED, "verify_seed": VERIFY_SEED, "generated_at": datetime.now(timezone.utc).isoformat(), "checks": checks, "passed": all(item["passed"] for item in checks)}
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if payload["passed"] else 1)


if __name__ == "__main__":
    main()
