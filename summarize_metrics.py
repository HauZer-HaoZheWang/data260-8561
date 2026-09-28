import csv
import statistics
from pathlib import Path


RAW_FILE = Path(
    "reports/hw04/raw/nplus1_measurements.csv"
)
OUTPUT_FILE = Path("reports/hw04/METRICS.md")


def percentile(values, percentage):
    values = sorted(values)
    index = round((len(values) - 1) * percentage)
    return values[index]


groups = {}

with RAW_FILE.open() as file:
    for row in csv.DictReader(file):
        key = (
            int(row["page_size"]),
            row["version"],
        )

        groups.setdefault(key, []).append(row)


rows = []

for (page_size, version), values in sorted(groups.items()):
    latencies = [
        float(row["latency_ms"])
        for row in values
    ]

    sql_counts = [
        int(row["sql_statements"])
        for row in values
    ]

    rows.append(
        {
            "page_size": page_size,
            "version": version,
            "sql": statistics.median(sql_counts),
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
        }
    )


lines = [
    "# HW4 N+1 Metrics",
    "",
    "| Page size | Version | SQL statements/request | p50 ms | p95 ms | p99 ms |",
    "|---:|---|---:|---:|---:|---:|",
]

for row in rows:
    lines.append(
        f"| {row['page_size']} | "
        f"{row['version']} | "
        f"{row['sql']} | "
        f"{row['p50']:.3f} | "
        f"{row['p95']:.3f} | "
        f"{row['p99']:.3f} |"
    )

lines.extend(
    [
        "",
        "## Speed-up",
        "",
    ]
)

for page_size in [10, 50, 200]:
    naive = next(
        row for row in rows
        if row["page_size"] == page_size
        and row["version"] == "naive"
    )

    fixed = next(
        row for row in rows
        if row["page_size"] == page_size
        and row["version"] == "fixed"
    )

    speedup = naive["p50"] / fixed["p50"]

    lines.append(
        f"- Page size {page_size}: "
        f"{speedup:.2f}x faster by p50 latency"
    )

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE.write_text("\n".join(lines))

print("\n".join(lines))
print("")
print(f"saved={OUTPUT_FILE}")
