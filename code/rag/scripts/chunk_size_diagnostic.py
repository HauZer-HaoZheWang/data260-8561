"""Measure MiniLM token lengths for all HW3 chunking techniques.

This diagnostic compares token, semantic 95, semantic 80, and
sentence-window chunk sizes across the complete 100-document corpus.

The output is saved as:
reports/hw03/raw/chunk_size_diagnostic.csv
"""

import csv
import sys
import time
from datetime import datetime
from pathlib import Path

from transformers import AutoTokenizer
from transformers import logging as transformers_logging


#Get the scripts folder
SCRIPT_DIR = Path(__file__).resolve().parent

#Get the code/rag folder
RAG_DIR = SCRIPT_DIR.parent

#Allow this script to import files from code/rag
if str(RAG_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(RAG_DIR)
    )

from chunkers import (  # noqa: E402
    build_semantic_nodes,
    build_sentence_window_nodes,
    build_token_nodes,
)
from pipeline import (  # noqa: E402
    EMBED_MODEL_NAME,
    REPORTS_DIR,
    configure_embeddings,
    load_corpus,
)


#MiniLM truncates sequences above this limit
MODEL_TOKEN_LIMIT = 256

#Save machine readable diagnostic output here
OUTPUT_PATH = (
    REPORTS_DIR
    / "raw"
    / "chunk_size_diagnostic.csv"
)

#Hide tokenizer warnings for intentionally long chunks
transformers_logging.set_verbosity_error()


def count_model_tokens(
    nodes,
    tokenizer
):
    """Count MiniLM WordPiece tokens in every node"""

    token_counts = []

    for node in nodes:
        token_ids = tokenizer.encode(
            node.text,
            add_special_tokens=False,
            truncation=False
        )

        token_counts.append(
            len(token_ids)
        )

    return sorted(
        token_counts
    )


def summarize_nodes(
    technique,
    percentile,
    nodes,
    elapsed_seconds,
    tokenizer
):
    """Create one diagnostic summary row"""

    token_counts = count_model_tokens(
        nodes,
        tokenizer
    )

    if not token_counts:
        raise ValueError(
            f"No nodes were created for {technique}"
        )

    node_count = len(
        token_counts
    )

    middle_index = (
        node_count // 2
    )

    median_tokens = token_counts[
        middle_index
    ]

    p90_index = min(
        int(node_count * 0.9),
        node_count - 1
    )

    p90_tokens = token_counts[
        p90_index
    ]

    max_tokens = max(
        token_counts
    )

    over_limit_count = sum(
        1
        for token_count in token_counts
        if token_count > MODEL_TOKEN_LIMIT
    )

    over_limit_percent = (
        over_limit_count
        / node_count
        * 100
    )

    #This is an estimate based on the 256-token limit
    estimated_lost_tokens = sum(
        max(
            0,
            token_count - MODEL_TOKEN_LIMIT
        )
        for token_count in token_counts
    )

    return {
        "technique": technique,
        "percentile": percentile,
        "nodes": node_count,
        "median_tokens": median_tokens,
        "p90_tokens": p90_tokens,
        "max_tokens": max_tokens,
        "over_256_count": over_limit_count,
        "over_256_pct": round(
            over_limit_percent,
            2
        ),
        "lost_tokens": estimated_lost_tokens,
        "elapsed_seconds": round(
            elapsed_seconds,
            3
        ),
    }


def print_row(
    row
):
    """Print one diagnostic result"""

    print(
        f"{row['technique']:<20}"
        f"p={str(row['percentile']):<5}"
        f"nodes={row['nodes']:5d}  "
        f"median={row['median_tokens']:5d}  "
        f"p90={row['p90_tokens']:5d}  "
        f"max={row['max_tokens']:5d}  "
        f"over256={row['over_256_count']:4d} "
        f"({row['over_256_pct']:6.2f}%)  "
        f"lost={row['lost_tokens']:7d}  "
        f"time={row['elapsed_seconds']:8.3f}s"
    )


def main():
    """Run the full-corpus chunk size diagnostic"""

    started_at = datetime.now().astimezone()

    print(
        "Chunk size diagnostic started:",
        started_at.isoformat(
            timespec="seconds"
        )
    )

    print(
        f"Embedding model: {EMBED_MODEL_NAME}"
    )

    print(
        f"Model token limit: {MODEL_TOKEN_LIMIT}"
    )

    print()

    #Load the tokenizer used by MiniLM
    tokenizer = AutoTokenizer.from_pretrained(
        EMBED_MODEL_NAME
    )

    #Configure local embeddings and disable generation
    embed_model = configure_embeddings()

    #Use all 100 corpus documents
    documents = load_corpus()

    total_characters = sum(
        len(document.text)
        for document in documents
    )

    print(
        f"Documents: {len(documents)}"
    )

    print(
        f"Characters: {total_characters}"
    )

    print()

    rows = []

    #Run fixed token chunking
    token_nodes, token_seconds = (
        build_token_nodes(
            documents
        )
    )

    rows.append(
        summarize_nodes(
            technique="token",
            percentile="n/a",
            nodes=token_nodes,
            elapsed_seconds=token_seconds,
            tokenizer=tokenizer
        )
    )

    print_row(
        rows[-1]
    )

    #Run the default semantic configuration
    semantic_95_nodes, semantic_95_seconds = (
        build_semantic_nodes(
            documents,
            embed_model,
            percentile=95
        )
    )

    rows.append(
        summarize_nodes(
            technique="semantic_95",
            percentile=95,
            nodes=semantic_95_nodes,
            elapsed_seconds=semantic_95_seconds,
            tokenizer=tokenizer
        )
    )

    print_row(
        rows[-1]
    )

    #Run the tuned semantic ablation
    semantic_80_nodes, semantic_80_seconds = (
        build_semantic_nodes(
            documents,
            embed_model,
            percentile=80
        )
    )

    rows.append(
        summarize_nodes(
            technique="semantic_tuned_80",
            percentile=80,
            nodes=semantic_80_nodes,
            elapsed_seconds=semantic_80_seconds,
            tokenizer=tokenizer
        )
    )

    print_row(
        rows[-1]
    )

    #Run sentence-window chunking
    window_nodes, window_seconds = (
        build_sentence_window_nodes(
            documents
        )
    )

    rows.append(
        summarize_nodes(
            technique="sentence_window",
            percentile="n/a",
            nodes=window_nodes,
            elapsed_seconds=window_seconds,
            tokenizer=tokenizer
        )
    )

    print_row(
        rows[-1]
    )

    #Create the required raw output folder
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "technique",
        "percentile",
        "nodes",
        "median_tokens",
        "p90_tokens",
        "max_tokens",
        "over_256_count",
        "over_256_pct",
        "lost_tokens",
        "elapsed_seconds",
    ]

    #Write the complete diagnostic table
    with OUTPUT_PATH.open(
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

    finished_at = datetime.now().astimezone()

    print()
    print(
        f"CSV saved to: {OUTPUT_PATH}"
    )

    print(
        "Chunk size diagnostic finished:",
        finished_at.isoformat(
            timespec="seconds"
        )
    )

    print(
        "Total elapsed time:",
        f"{(finished_at - started_at).total_seconds():.1f} seconds"
    )


if __name__ == "__main__":
    main()
