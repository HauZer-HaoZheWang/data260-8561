"""Analyze completed HW3 retrieval results.

This script:
1. Calculates Recall@1 from existing retrieval JSON files.
2. Compares Semantic 95 and Semantic 80 Top-1 chunk text.
3. Saves all analysis as machine readable CSV files.

No index is rebuilt and no embedding model is loaded.
"""

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path


#Get the repository root folder
REPO_DIR = Path(__file__).resolve().parents[3]

#Read existing experiment output here
RAW_DIR = (
    REPO_DIR
    / "reports"
    / "hw03"
    / "raw"
)

#Save Recall@1 details here
RECALL_DETAIL_PATH = (
    RAW_DIR
    / "recall_at_1.csv"
)

#Save Recall@1 summary here
RECALL_SUMMARY_PATH = (
    RAW_DIR
    / "recall_at_1_summary.csv"
)

#Save Semantic Top-1 comparison here
SEMANTIC_COMPARISON_PATH = (
    RAW_DIR
    / "semantic_top1_comparison.csv"
)

#Analyze the required techniques and the ablation
TECHNIQUES = [
    "token",
    "semantic_95",
    "sentence_window",
    "semantic_tuned_80",
]

QUESTION_IDS = [
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "Q5",
]


def load_result(
    technique,
    question_id
):
    """Load one existing retrieval result"""

    result_path = (
        RAW_DIR
        / technique
        / f"{question_id}.json"
    )

    if not result_path.exists():
        raise FileNotFoundError(
            f"Result file not found: {result_path}"
        )

    return json.loads(
        result_path.read_text(
            encoding="utf-8"
        )
    )


def text_sha256(
    text
):
    """Calculate SHA-256 for one text string"""

    return hashlib.sha256(
        text.encode(
            "utf-8"
        )
    ).hexdigest()


def write_csv(
    output_path,
    rows,
    fieldnames
):
    """Write rows to a CSV file"""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(
            rows
        )


def analyze_recall_at_1():
    """Calculate Recall@1 for every technique"""

    detail_rows = []
    summary_rows = []

    for technique in TECHNIQUES:
        hits = 0

        for question_id in QUESTION_IDS:
            result = load_result(
                technique,
                question_id
            )

            expected_source = result[
                "expected_source"
            ]

            top_result = result[
                "results"
            ][0]

            top_source = top_result[
                "source_file"
            ]

            recall_at_1 = int(
                top_source
                == expected_source
            )

            hits += recall_at_1

            detail_rows.append(
                {
                    "technique": technique,
                    "question_id": question_id,
                    "expected_source": expected_source,
                    "top_1_source": top_source,
                    "recall_at_1": recall_at_1,
                    "store_score": round(
                        top_result[
                            "store_score"
                        ],
                        6
                    ),
                    "manual_cosine": round(
                        top_result[
                            "cosine_similarity"
                        ],
                        6
                    ),
                }
            )

        recall_rate = (
            hits
            / len(QUESTION_IDS)
        )

        summary_rows.append(
            {
                "technique": technique,
                "questions": len(
                    QUESTION_IDS
                ),
                "top_1_hits": hits,
                "recall_at_1": round(
                    recall_rate,
                    3
                ),
            }
        )

    write_csv(
        RECALL_DETAIL_PATH,
        detail_rows,
        [
            "technique",
            "question_id",
            "expected_source",
            "top_1_source",
            "recall_at_1",
            "store_score",
            "manual_cosine",
        ]
    )

    write_csv(
        RECALL_SUMMARY_PATH,
        summary_rows,
        [
            "technique",
            "questions",
            "top_1_hits",
            "recall_at_1",
        ]
    )

    return summary_rows


def compare_semantic_top_1():
    """Compare Semantic 95 and Semantic 80 Top-1 chunks"""

    comparison_rows = []

    for question_id in QUESTION_IDS:
        semantic_95 = load_result(
            "semantic_95",
            question_id
        )

        semantic_80 = load_result(
            "semantic_tuned_80",
            question_id
        )

        top_95 = semantic_95[
            "results"
        ][0]

        top_80 = semantic_80[
            "results"
        ][0]

        text_95 = top_95[
            "chunk_text"
        ]

        text_80 = top_80[
            "chunk_text"
        ]

        hash_95 = text_sha256(
            text_95
        )

        hash_80 = text_sha256(
            text_80
        )

        same_text = (
            text_95
            == text_80
        )

        same_source = (
            top_95["source_file"]
            == top_80["source_file"]
        )

        same_store_score = (
            abs(
                top_95["store_score"]
                - top_80["store_score"]
            )
            < 0.000000001
        )

        same_cosine = (
            abs(
                top_95[
                    "cosine_similarity"
                ]
                - top_80[
                    "cosine_similarity"
                ]
            )
            < 0.000000001
        )

        comparison_rows.append(
            {
                "question_id": question_id,
                "semantic_95_source": (
                    top_95["source_file"]
                ),
                "semantic_80_source": (
                    top_80["source_file"]
                ),
                "semantic_95_length": len(
                    text_95
                ),
                "semantic_80_length": len(
                    text_80
                ),
                "semantic_95_sha256": hash_95,
                "semantic_80_sha256": hash_80,
                "same_source": same_source,
                "same_text": same_text,
                "same_store_score": (
                    same_store_score
                ),
                "same_manual_cosine": (
                    same_cosine
                ),
            }
        )

    write_csv(
        SEMANTIC_COMPARISON_PATH,
        comparison_rows,
        [
            "question_id",
            "semantic_95_source",
            "semantic_80_source",
            "semantic_95_length",
            "semantic_80_length",
            "semantic_95_sha256",
            "semantic_80_sha256",
            "same_source",
            "same_text",
            "same_store_score",
            "same_manual_cosine",
        ]
    )

    return comparison_rows


def main():
    """Run result analysis"""

    started_at = datetime.now().astimezone()

    print(
        "Retrieval result analysis started:",
        started_at.isoformat(
            timespec="seconds"
        )
    )

    print()

    recall_rows = analyze_recall_at_1()

    print(
        "Recall@1 summary"
    )

    print(
        "-" * 60
    )

    for row in recall_rows:
        print(
            f"{row['technique']:<22}"
            f"hits={row['top_1_hits']}/"
            f"{row['questions']}  "
            f"Recall@1="
            f"{row['recall_at_1']:.3f}"
        )

    print()

    semantic_rows = compare_semantic_top_1()

    print(
        "Semantic 95 vs Semantic 80 Top-1 comparison"
    )

    print(
        "-" * 60
    )

    identical_count = 0

    for row in semantic_rows:
        if row["same_text"]:
            identical_count += 1

        print(
            f"{row['question_id']}: "
            f"same_source={row['same_source']}  "
            f"same_text={row['same_text']}  "
            f"same_store_score="
            f"{row['same_store_score']}  "
            f"same_cosine="
            f"{row['same_manual_cosine']}"
        )

    print()

    print(
        "Identical Semantic Top-1 chunks:",
        f"{identical_count}/"
        f"{len(semantic_rows)}"
    )

    print()

    print(
        f"Recall details saved to: "
        f"{RECALL_DETAIL_PATH}"
    )

    print(
        f"Recall summary saved to: "
        f"{RECALL_SUMMARY_PATH}"
    )

    print(
        "Semantic comparison saved to: "
        f"{SEMANTIC_COMPARISON_PATH}"
    )

    finished_at = datetime.now().astimezone()

    print()

    print(
        "Analysis finished:",
        finished_at.isoformat(
            timespec="seconds"
        )
    )


if __name__ == "__main__":
    main()
    