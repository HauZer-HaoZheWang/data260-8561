"""Measure MiniLM's effective input length and validate vector-store scores.

This diagnostic performs two checks:

1. Recompute chunk-size statistics using 254 content tokens. MiniLM accepts
   256 total tokens, but [CLS] and [SEP] occupy two positions.
2. Compare the vector-store score with manual cosine similarity computed from:
   a. visible node text only
   b. the exact MetadataMode.EMBED content used by LlamaIndex

The script writes new diagnostic CSV files and does not overwrite the formal
retrieval experiment results.
"""

import csv
import sys
from pathlib import Path

import numpy as np
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import MetadataMode, QueryBundle
from transformers import AutoTokenizer


SCRIPT_DIR = Path(__file__).resolve().parent
RAG_DIR = SCRIPT_DIR.parent
REPO_DIR = RAG_DIR.parent.parent
RAW_DIR = REPO_DIR / "reports" / "hw03" / "raw"

sys.path.insert(
    0,
    str(RAG_DIR),
)

from chunkers import (  # noqa: E402
    SEMANTIC_BREAKPOINT_PERCENTILE,
    SEMANTIC_BREAKPOINT_PERCENTILE_TUNED,
    build_semantic_nodes,
    build_sentence_window_nodes,
    build_token_nodes,
)
from pipeline import (  # noqa: E402
    EMBED_MODEL_NAME,
    configure_embeddings,
    cosine_similarity,
    load_corpus,
)


MODEL_SEQUENCE_LIMIT = 256
SPECIAL_TOKEN_COUNT = 2
CONTENT_TOKEN_LIMIT = (
    MODEL_SEQUENCE_LIMIT
    - SPECIAL_TOKEN_COUNT
)

VALIDATION_QUERY = (
    "In the ARV-6723 dose escalation study, over how many days "
    "after the first administration are dose-limiting toxicities assessed?"
)

VALIDATION_EXPECTED_SOURCE = "NCT07749586.txt"
TOP_K = 5


def percentile_value(
    sorted_values,
    fraction,
):
    """Return a percentile value using the experiment's original method."""

    if not sorted_values:
        return 0

    index = min(
        int(len(sorted_values) * fraction),
        len(sorted_values) - 1,
    )

    return sorted_values[index]


def calculate_token_statistics(
    nodes,
    tokenizer,
    metadata_mode,
):
    """Calculate token-length statistics for one node content representation."""

    token_counts = []

    for node in nodes:
        content = node.get_content(
            metadata_mode=metadata_mode,
        )

        count = len(
            tokenizer.encode(
                content,
                add_special_tokens=False,
                truncation=False,
            )
        )

        token_counts.append(count)

    token_counts.sort()

    over_limit_counts = [
        count
        for count in token_counts
        if count > CONTENT_TOKEN_LIMIT
    ]

    lost_tokens = sum(
        count - CONTENT_TOKEN_LIMIT
        for count in over_limit_counts
    )

    return {
        "nodes": len(token_counts),
        "median_tokens": token_counts[
            len(token_counts) // 2
        ],
        "p90_tokens": percentile_value(
            token_counts,
            0.9,
        ),
        "max_tokens": max(token_counts),
        "over_254_count": len(over_limit_counts),
        "over_254_pct": (
            len(over_limit_counts)
            / len(token_counts)
            * 100
        ),
        "estimated_truncated_tokens": lost_tokens,
    }


def write_effective_input_csv(
    rows,
):
    """Save effective input statistics."""

    output_path = (
        RAW_DIR
        / "effective_input_diagnostic.csv"
    )

    fieldnames = [
        "technique",
        "content_variant",
        "nodes",
        "median_tokens",
        "p90_tokens",
        "max_tokens",
        "over_254_count",
        "over_254_pct",
        "estimated_truncated_tokens",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    return output_path


def validate_store_scores(
    nodes,
    embed_model,
):
    """Compare store scores with two independently computed cosine scores."""

    index = VectorStoreIndex(
        nodes,
        embed_model=embed_model,
        show_progress=True,
    )

    query_embedding = np.asarray(
        embed_model.get_query_embedding(
            VALIDATION_QUERY
        ),
        dtype=float,
    )

    retriever = index.as_retriever(
        similarity_top_k=TOP_K,
    )

    query_bundle = QueryBundle(
        query_str=VALIDATION_QUERY,
        embedding=query_embedding.tolist(),
    )

    results = retriever.retrieve(
        query_bundle
    )

    rows = []

    for rank, result in enumerate(
        results,
        start=1,
    ):
        node = result.node

        visible_text = node.get_content(
            metadata_mode=MetadataMode.NONE,
        )

        embed_content = node.get_content(
            metadata_mode=MetadataMode.EMBED,
        )

        visible_embedding = (
            embed_model.get_text_embedding(
                visible_text
            )
        )

        metadata_embedding = (
            embed_model.get_text_embedding(
                embed_content
            )
        )

        visible_cosine = cosine_similarity(
            query_embedding,
            visible_embedding,
        )

        metadata_cosine = cosine_similarity(
            query_embedding,
            metadata_embedding,
        )

        store_score = float(
            result.score
        )

        source_file = node.metadata.get(
            "source_file",
            "",
        )

        row = {
            "rank": rank,
            "source_file": source_file,
            "expected_source": (
                VALIDATION_EXPECTED_SOURCE
            ),
            "store_score": store_score,
            "visible_text_cosine": visible_cosine,
            "metadata_embed_cosine": metadata_cosine,
            "store_minus_visible": (
                store_score
                - visible_cosine
            ),
            "store_minus_metadata": (
                store_score
                - metadata_cosine
            ),
            "visible_characters": len(
                visible_text
            ),
            "embed_content_characters": len(
                embed_content
            ),
            "metadata_keys": "|".join(
                sorted(
                    str(key)
                    for key in node.metadata
                )
            ),
        }

        rows.append(row)

    output_path = (
        RAW_DIR
        / "metadata_score_validation.csv"
    )

    fieldnames = [
        "rank",
        "source_file",
        "expected_source",
        "store_score",
        "visible_text_cosine",
        "metadata_embed_cosine",
        "store_minus_visible",
        "store_minus_metadata",
        "visible_characters",
        "embed_content_characters",
        "metadata_keys",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    return rows, output_path


def print_statistics_row(
    technique,
    content_variant,
    statistics,
):
    """Print one readable diagnostic row."""

    print(
        f"{technique:20s} "
        f"{content_variant:12s} "
        f"nodes={statistics['nodes']:5d}  "
        f"median={statistics['median_tokens']:5d}  "
        f"p90={statistics['p90_tokens']:5d}  "
        f"max={statistics['max_tokens']:5d}  "
        f"over254="
        f"{statistics['over_254_count']:5d} "
        f"("
        f"{statistics['over_254_pct']:6.2f}%"
        f")  "
        f"lost="
        f"{statistics['estimated_truncated_tokens']:7d}"
    )


def main():
    """Run the effective-input and metadata-score diagnostics."""

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Effective input diagnostic"
    )

    print(
        f"Embedding model: {EMBED_MODEL_NAME}"
    )

    print(
        "Model sequence limit: "
        f"{MODEL_SEQUENCE_LIMIT}"
    )

    print(
        "Reserved special-token positions: "
        f"{SPECIAL_TOKEN_COUNT}"
    )

    print(
        "Effective content-token limit: "
        f"{CONTENT_TOKEN_LIMIT}"
    )

    print()

    tokenizer = AutoTokenizer.from_pretrained(
        EMBED_MODEL_NAME
    )

    embed_model = configure_embeddings()
    documents = load_corpus()

    print(
        f"Documents: {len(documents)}"
    )

    print(
        "Characters: "
        f"{sum(len(document.text) for document in documents)}"
    )

    print()
    print(
        "Building all chunking configurations"
    )

    token_nodes, _ = build_token_nodes(
        documents
    )

    semantic_95_nodes, _ = (
        build_semantic_nodes(
            documents,
            embed_model,
            percentile=(
                SEMANTIC_BREAKPOINT_PERCENTILE
            ),
        )
    )

    sentence_window_nodes, _ = (
        build_sentence_window_nodes(
            documents
        )
    )

    semantic_80_nodes, _ = (
        build_semantic_nodes(
            documents,
            embed_model,
            percentile=(
                SEMANTIC_BREAKPOINT_PERCENTILE_TUNED
            ),
        )
    )

    techniques = [
        (
            "token",
            token_nodes,
        ),
        (
            "semantic_95",
            semantic_95_nodes,
        ),
        (
            "sentence_window",
            sentence_window_nodes,
        ),
        (
            "semantic_tuned_80",
            semantic_80_nodes,
        ),
    ]

    print()
    print(
        "Token statistics"
    )

    print(
        "-" * 120
    )

    rows = []

    for technique, nodes in techniques:
        variants = [
            (
                "visible_text",
                MetadataMode.NONE,
            ),
            (
                "index_input",
                MetadataMode.EMBED,
            ),
        ]

        for (
            content_variant,
            metadata_mode,
        ) in variants:
            statistics = (
                calculate_token_statistics(
                    nodes,
                    tokenizer,
                    metadata_mode,
                )
            )

            row = {
                "technique": technique,
                "content_variant": (
                    content_variant
                ),
                **statistics,
            }

            rows.append(row)

            print_statistics_row(
                technique,
                content_variant,
                statistics,
            )

    effective_input_path = (
        write_effective_input_csv(
            rows
        )
    )

    print()
    print(
        "Store-score validation"
    )

    print(
        "-" * 120
    )

    print(
        f"Technique: token"
    )

    print(
        f"Question: {VALIDATION_QUERY}"
    )

    print(
        "Visible cosine uses MetadataMode.NONE."
    )

    print(
        "Metadata cosine uses MetadataMode.EMBED."
    )

    validation_rows, validation_path = (
        validate_store_scores(
            token_nodes,
            embed_model,
        )
    )

    print()

    print(
        f"{'Rank':<6}"
        f"{'Source':<22}"
        f"{'Store':>12}"
        f"{'Visible':>12}"
        f"{'Metadata':>12}"
        f"{'Delta visible':>16}"
        f"{'Delta metadata':>17}"
    )

    print(
        "-" * 97
    )

    for row in validation_rows:
        print(
            f"{row['rank']:<6}"
            f"{row['source_file']:<22}"
            f"{row['store_score']:>12.6f}"
            f"{row['visible_text_cosine']:>12.6f}"
            f"{row['metadata_embed_cosine']:>12.6f}"
            f"{row['store_minus_visible']:>16.8f}"
            f"{row['store_minus_metadata']:>17.8f}"
        )

    maximum_metadata_delta = max(
        abs(
            row["store_minus_metadata"]
        )
        for row in validation_rows
    )

    maximum_visible_delta = max(
        abs(
            row["store_minus_visible"]
        )
        for row in validation_rows
    )

    print()
    print(
        "Maximum absolute store-versus-visible delta: "
        f"{maximum_visible_delta:.10f}"
    )

    print(
        "Maximum absolute store-versus-metadata delta: "
        f"{maximum_metadata_delta:.10f}"
    )

    if maximum_metadata_delta < 1e-5:
        print(
            "Result: MetadataMode.EMBED reproduces "
            "the vector-store scores within floating-point tolerance."
        )
    else:
        print(
            "Result: MetadataMode.EMBED does not fully reproduce "
            "the vector-store scores. Further inspection is required."
        )

    print()
    print(
        "Effective input CSV saved to: "
        f"{effective_input_path}"
    )

    print(
        "Metadata score CSV saved to: "
        f"{validation_path}"
    )


if __name__ == "__main__":
    main()