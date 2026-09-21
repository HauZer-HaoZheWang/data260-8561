"""Print one saved retrieval block for report screenshots."""

import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent.parent

RUN_LOG_PATH = (
    REPO_DIR
    / "reports"
    / "hw03"
    / "RUN_LOG.txt"
)

TECHNIQUES = (
    "token",
    "semantic_95",
    "sentence_window",
)


def parse_arguments():
    """Read command-line arguments"""

    parser = argparse.ArgumentParser(
        description=(
            "Print one retrieval output block "
            "from the saved HW3 run log"
        )
    )

    parser.add_argument(
        "--technique",
        required=True,
        choices=TECHNIQUES,
    )

    parser.add_argument(
        "--question",
        default="Q2",
    )

    return parser.parse_args()


def find_output_block(
    log_text,
    technique,
    question_id,
):
    """Return the last matching output block"""

    needle = (
        f"Technique: {technique}\n"
        f"Question: {question_id} -"
    )

    technique_start = log_text.rfind(needle)

    if technique_start == -1:
        raise ValueError(
            "Output block was not found for "
            f"{technique} {question_id}"
        )

    separator = "=" * 100

    block_start = log_text.rfind(
        separator,
        0,
        technique_start,
    )

    if block_start == -1:
        block_start = technique_start

    block_end = log_text.find(
        separator,
        technique_start,
    )

    if block_end == -1:
        block_end = len(log_text)
    else:
        block_end += len(separator)

    return log_text[
        block_start:block_end
    ].strip()


def main():
    """Print the saved report example"""

    arguments = parse_arguments()

    if not RUN_LOG_PATH.exists():
        raise FileNotFoundError(
            f"Run log not found: {RUN_LOG_PATH}"
        )

    log_text = RUN_LOG_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )

    output_block = find_output_block(
        log_text=log_text,
        technique=arguments.technique,
        question_id=arguments.question,
    )

    print("DATA 260 HW3 RETRIEVAL OUTPUT")
    print(f"Technique: {arguments.technique}")
    print(f"Question: {arguments.question}")
    print()

    print(output_block)


if __name__ == "__main__":
    main()