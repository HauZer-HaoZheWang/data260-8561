import csv
import json
import sys
from pathlib import Path

from sqlalchemy import text


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "code" / "web_application"
FRONTEND = ROOT / "code" / "frontend"
REPORTS = ROOT / "reports" / "hw04"

sys.path.insert(0, str(BACKEND))

from database import db_session_basede26


checks = {}


def record(name, passed, detail):
    checks[name] = {
        "passed": bool(passed),
        "detail": str(detail),
    }


required_files = [
    BACKEND / "database.py",
    BACKEND / "models.py",
    BACKEND / "performance.py",
    FRONTEND / "src" / "App.jsx",
    ROOT / "code" / "rag" / "rag.py",
    REPORTS / "METRICS.md",
    REPORTS / "RUN_LOG.txt",
    REPORTS / "AI_USE.md",
    REPORTS / "RAG_ANALYSIS.md",
]

missing = [
    str(path.relative_to(ROOT))
    for path in required_files
    if not path.exists()
]

record(
    "required_files",
    not missing,
    "all present" if not missing else missing,
)

database_code = (
    BACKEND / "database.py"
).read_text(encoding="utf-8")

record(
    "required_database_variable",
    "db_session_basede26" in database_code,
    "db_session_basede26 found",
)

main_code = (
    BACKEND / "main.py"
).read_text(encoding="utf-8")

record(
    "no_signed_session_middleware",
    "SessionMiddleware" not in main_code,
    "SessionMiddleware absent from main.py",
)

frontend_code = (
    FRONTEND / "src" / "App.jsx"
).read_text(encoding="utf-8")

frontend_terms = [
    "function Login",
    "function Home",
    "function CreateRecord",
    "function UpdateRecord",
    "function DeleteRecord",
    'path="/"',
    'path="/login"',
    'path="/create"',
    'path="/update/:id"',
    'path="/delete/:id"',
]

missing_frontend = [
    term
    for term in frontend_terms
    if term not in frontend_code
]

record(
    "react_components_and_routes",
    not missing_frontend,
    "all present" if not missing_frontend else missing_frontend,
)

raw_path = REPORTS / "raw" / "nplus1_measurements.csv"

with raw_path.open(encoding="utf-8") as csv_file:
    raw_rows = list(csv.DictReader(csv_file))

record(
    "nplus1_raw_measurements",
    len(raw_rows) == 180,
    f"{len(raw_rows)} rows",
)

combinations = {
    (
        row["version"],
        int(row["page_size"]),
    )
    for row in raw_rows
}

expected_combinations = {
    (version, page_size)
    for version in ["naive", "fixed"]
    for page_size in [10, 50, 200]
}

record(
    "nplus1_combinations",
    combinations == expected_combinations,
    sorted(combinations),
)

screenshots = list(
    (REPORTS / "screenshots").glob("*.png")
)

record(
    "screenshots",
    len(screenshots) >= 70,
    f"{len(screenshots)} PNG files",
)

rag_results = json.loads(
    (REPORTS / "rag_results.json").read_text(
        encoding="utf-8"
    )
)

record(
    "rag_result_count",
    len(rag_results) == 36,
    f"{len(rag_results)} results",
)

configurations = {
    row["configuration"]
    for row in rag_results
}

record(
    "rag_configurations",
    configurations == {"A", "B", "C"},
    sorted(configurations),
)

k_values = {
    int(row["top_k"])
    for row in rag_results
    if row["configuration"] == "C"
}

record(
    "rag_k_sweep",
    {1, 3, 5}.issubset(k_values),
    sorted(k_values),
)

refusal_text = (
    "I cannot answer this question from the provided documents"
)

refusal_checks = [
    row["answer"] == refusal_text
    for row in rag_results
    if (
        row["configuration"] == "C"
        and row["question_id"] in {"Q5", "Q6"}
    )
]

record(
    "rag_q5_q6_refusal",
    refusal_checks and all(refusal_checks),
    f"{sum(refusal_checks)}/{len(refusal_checks)} correct refusals",
)

with db_session_basede26.connect() as connection:
    database_name = connection.execute(
        text("SELECT DATABASE()")
    ).scalar()

    trial_count = connection.execute(
        text("SELECT COUNT(*) FROM trials")
    ).scalar()

    detail_count = connection.execute(
        text("SELECT COUNT(*) FROM trial_details")
    ).scalar()

    table_count = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name IN
                  ('users', 'sessions', 'trials', 'trial_details')
            """
        )
    ).scalar()

record(
    "mysql_database",
    database_name == "s8561_rel",
    database_name,
)

record(
    "mysql_tables",
    table_count == 4,
    f"{table_count}/4 tables",
)

record(
    "seeded_trials",
    trial_count == 5000,
    f"{trial_count} trials",
)

record(
    "seeded_trial_details",
    detail_count == 200,
    f"{detail_count} trial details",
)

all_passed = all(
    item["passed"]
    for item in checks.values()
)

verification = {
    "sid4": 8561,
    "status": "PASS" if all_passed else "FAIL",
    "checks": checks,
}

output_path = REPORTS / "verification.json"

output_path.write_text(
    json.dumps(verification, indent=2),
    encoding="utf-8",
)

print(json.dumps(verification, indent=2))
print(f"Saved: {output_path}")
