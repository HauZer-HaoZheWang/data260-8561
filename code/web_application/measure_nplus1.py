import csv
import json
import os
import statistics
import time
from pathlib import Path
from urllib import request


BASE_URL = "http://127.0.0.1:8461"
EMAIL = os.getenv(
    "HW4_EMAIL",
    "hw4test20260926@example.com",
)
PASSWORD = os.getenv(
    "HW4_PASSWORD",
    "TestPass123!",
)

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "reports" / "hw04" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

RAW_FILE = RAW_DIR / "nplus1_measurements.csv"


def percentile(values, percentage):
    values = sorted(values)
    index = round((len(values) - 1) * percentage)
    return values[index]


def make_request(opener, path):
    start = time.perf_counter()

    with opener.open(
        request.Request(
            BASE_URL + path,
            method="GET",
        )
    ) as response:
        body = response.read()
        status = response.status
        sql_count = response.headers.get(
            "X-SQL-Statements",
            "",
        )

    elapsed_ms = (time.perf_counter() - start) * 1000
    records = json.loads(body)

    return {
        "status": status,
        "sql_statements": int(sql_count),
        "latency_ms": round(elapsed_ms, 3),
        "records": len(records),
    }


def login():
    cookie_jar = request.HTTPCookieProcessor()
    opener = request.build_opener(cookie_jar)

    payload = json.dumps(
        {
            "email": EMAIL,
            "password": PASSWORD,
        }
    ).encode()

    login_request = request.Request(
        BASE_URL + "/auth/login",
        data=payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with opener.open(login_request) as response:
        if response.status != 200:
            raise RuntimeError(
                f"Login failed: {response.status}"
            )

    return opener


def main():
    opener = login()
    rows = []
    summary = []

    for page_size in [10, 50, 200]:
        for version in ["naive", "fixed"]:
            latencies = []
            sql_counts = []

            for run_number in range(1, 31):
                result = make_request(
                    opener,
                    f"/api/performance/{version}"
                    f"?page_size={page_size}",
                )

                row = {
                    "page_size": page_size,
                    "version": version,
                    "run": run_number,
                    **result,
                }

                rows.append(row)
                latencies.append(result["latency_ms"])
                sql_counts.append(result["sql_statements"])

            summary_row = {
                "page_size": page_size,
                "version": version,
                "sql_statements": statistics.median(
                    sql_counts
                ),
                "p50_ms": round(
                    percentile(latencies, 0.50),
                    3,
                ),
                "p95_ms": round(
                    percentile(latencies, 0.95),
                    3,
                ),
                "p99_ms": round(
                    percentile(latencies, 0.99),
                    3,
                ),
            }

            summary.append(summary_row)
            print(summary_row)

    with RAW_FILE.open(
        "w",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys(),
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"raw_rows={len(rows)}")
    print(f"raw_file={RAW_FILE}")


if __name__ == "__main__":
    main()
