"""Run the complete HW3 retrieval comparison.

Main comparison:
1. Token chunking
2. Semantic chunking with percentile 95
3. Sentence-window chunking

Additional ablation:
4. Semantic chunking with percentile 80

The experiment creates in-memory indexes and saves all retrieval results
under reports/hw03/raw.
"""

import argparse
import csv
import gc
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean

import yaml
from llama_index.core.schema import MetadataMode


#Get the code/rag folder
BASE_DIR = Path(__file__).resolve().parent

#Allow local imports when this file is run directly
if str(BASE_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(BASE_DIR)
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
from retrieval import (  # noqa: E402
    build_index,
    retrieve_query,
    save_json,
)


#Use five retrieved chunks for every question
TOP_K = 5

#Read questions committed before the experiment
QUESTIONS_PATH = (
    REPORTS_DIR
    / "questions.yaml"
)

#Store machine readable experiment output here
RAW_DIR = (
    REPORTS_DIR
    / "raw"
)


def load_questions():
    """Load and validate questions.yaml"""

    if not QUESTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Questions file not found: {QUESTIONS_PATH}"
        )

    question_data = yaml.safe_load(
        QUESTIONS_PATH.read_text(
            encoding="utf-8"
        )
    )

    questions = question_data.get(
        "questions",
        []
    )

    if len(questions) < 5:
        raise ValueError(
            "questions.yaml must contain at least five questions"
        )

    required_fields = {
        "id",
        "question",
        "expected_answer",
        "expected_source",
    }

    for question in questions:
        missing_fields = (
            required_fields
            - set(question)
        )

        if missing_fields:
            raise ValueError(
                f"Question is missing fields: "
                f"{sorted(missing_fields)}"
            )

    return questions


def average_node_length(
    nodes
):
    """Calculate average node length in characters"""

    lengths = [
        len(
            node.get_content(
                metadata_mode=MetadataMode.NONE
            )
        )
        for node in nodes
    ]

    if not lengths:
        return 0.0

    return mean(
        lengths
    )


def write_csv(
    output_path,
    rows,
    fieldnames
):
    """Write a list of dictionaries as CSV"""

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


def main():
    """Run all retrieval experiments"""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--include-tuned",
        action="store_true",
        help="Include the semantic percentile 80 ablation"
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=TOP_K
    )

    arguments = parser.parse_args()

    started_at = datetime.now().astimezone()

    print(
        "HW3 retrieval experiment started:",
        started_at.isoformat(
            timespec="seconds"
        )
    )

    print(
        f"Embedding model: {EMBED_MODEL_NAME}"
    )

    print(
        "Generation model: none"
    )

    print(
        f"Top-k: {arguments.top_k}"
    )

    print()

    #Create the raw output directory
    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    #Load experiment inputs
    questions = load_questions()
    embed_model = configure_embeddings()
    documents = load_corpus()

    print(
        f"Documents loaded: {len(documents)}"
    )

    print(
        f"Questions loaded: {len(questions)}"
    )

    print()

    #Define the required three techniques
    techniques = [
        {
            "name": "token",
            "group": "main",
            "builder": lambda: build_token_nodes(
                documents
            ),
        },
        {
            "name": "semantic_95",
            "group": "main",
            "builder": lambda: build_semantic_nodes(
                documents,
                embed_model,
                percentile=95
            ),
        },
        {
            "name": "sentence_window",
            "group": "main",
            "builder": (
                lambda: build_sentence_window_nodes(
                    documents
                )
            ),
        },
    ]

    #Add the optional semantic ablation
    if arguments.include_tuned:
        techniques.append(
            {
                "name": "semantic_tuned_80",
                "group": "ablation",
                "builder": (
                    lambda: build_semantic_nodes(
                        documents,
                        embed_model,
                        percentile=80
                    )
                ),
            }
        )

    all_outputs = []
    chunk_rows = []
    per_query_rows = []

    #Build and evaluate one technique at a time
    for technique in techniques:
        technique_name = technique["name"]

        print()
        print(
            "#" * 100
        )
        print(
            f"Building technique: {technique_name}"
        )
        print(
            "#" * 100
        )

        nodes, chunking_seconds = (
            technique["builder"]()
        )

        chunk_count = len(
            nodes
        )

        avg_chunk_length = average_node_length(
            nodes
        )

        print(
            f"Chunks: {chunk_count}"
        )

        print(
            "Average chunk length: "
            f"{avg_chunk_length:.2f} characters"
        )

        print(
            "Chunking time: "
            f"{chunking_seconds:.3f} seconds"
        )

        #Build one in-memory index for this technique
        index, indexing_seconds = build_index(
            nodes,
            embed_model
        )

        print(
            "Indexing time: "
            f"{indexing_seconds:.3f} seconds"
        )

        chunk_rows.append(
            {
                "technique": technique_name,
                "group": technique["group"],
                "chunks": chunk_count,
                "avg_chunk_length_chars": round(
                    avg_chunk_length,
                    3
                ),
                "chunking_seconds": round(
                    chunking_seconds,
                    3
                ),
                "indexing_seconds": round(
                    indexing_seconds,
                    3
                ),
            }
        )

        technique_output_dir = (
            RAW_DIR
            / technique_name
        )

        #Run all questions against this index
        for question in questions:
            output = retrieve_query(
                index=index,
                embed_model=embed_model,
                technique=technique_name,
                question_id=question["id"],
                question=question["question"],
                expected_answer=(
                    question["expected_answer"]
                ),
                expected_source=(
                    question["expected_source"]
                ),
                top_k=arguments.top_k
            )

            output["experiment_group"] = (
                technique["group"]
            )

            output["chunk_count"] = (
                chunk_count
            )

            output["avg_chunk_length_chars"] = (
                avg_chunk_length
            )

            output["chunking_seconds"] = (
                chunking_seconds
            )

            output["indexing_seconds"] = (
                indexing_seconds
            )

            output_path = (
                technique_output_dir
                / f"{question['id']}.json"
            )

            save_json(
                output,
                output_path
            )

            all_outputs.append(
                output
            )

            per_query_rows.append(
                {
                    "technique": technique_name,
                    "group": technique["group"],
                    "question_id": question["id"],
                    "expected_source": (
                        question["expected_source"]
                    ),
                    "top_1_cosine": round(
                        output["top_1_cosine"],
                        6
                    ),
                    "mean_at_k_cosine": round(
                        output["mean_at_k_cosine"],
                        6
                    ),
                    "recall_at_k": (
                        output["recall_at_k"]
                    ),
                    "retrieval_latency_ms": round(
                        output[
                            "retrieval_latency_ms"
                        ],
                        3
                    ),
                }
            )

        #Release the index before building the next one
        del index
        del nodes
        gc.collect()

    #Save every complete result as JSONL
    jsonl_path = (
        RAW_DIR
        / "retrieval_results.jsonl"
    )

    with jsonl_path.open(
        "w",
        encoding="utf-8"
    ) as jsonl_file:
        for output in all_outputs:
            jsonl_file.write(
                json.dumps(
                    output
                )
                + "\n"
            )

    #Save chunk and indexing measurements
    write_csv(
        RAW_DIR / "chunk_metrics.csv",
        chunk_rows,
        [
            "technique",
            "group",
            "chunks",
            "avg_chunk_length_chars",
            "chunking_seconds",
            "indexing_seconds",
        ]
    )

    #Save one metric row per question
    write_csv(
        RAW_DIR / "per_query_metrics.csv",
        per_query_rows,
        [
            "technique",
            "group",
            "question_id",
            "expected_source",
            "top_1_cosine",
            "mean_at_k_cosine",
            "recall_at_k",
            "retrieval_latency_ms",
        ]
    )

    #Calculate one summary row per technique
    summary_rows = []

    for technique in techniques:
        technique_name = technique["name"]

        technique_outputs = [
            output
            for output in all_outputs
            if output["technique"] == technique_name
        ]

        chunk_data = next(
            row
            for row in chunk_rows
            if row["technique"] == technique_name
        )

        summary_rows.append(
            {
                "technique": technique_name,
                "group": technique["group"],
                "chunks": chunk_data["chunks"],
                "avg_chunk_length_chars": (
                    chunk_data[
                        "avg_chunk_length_chars"
                    ]
                ),
                "mean_top_1_cosine": round(
                    mean(
                        output["top_1_cosine"]
                        for output in technique_outputs
                    ),
                    6
                ),
                "mean_at_k_cosine": round(
                    mean(
                        output["mean_at_k_cosine"]
                        for output in technique_outputs
                    ),
                    6
                ),
                "recall_at_k": round(
                    mean(
                        output["recall_at_k"]
                        for output in technique_outputs
                    ),
                    3
                ),
                "mean_retrieval_latency_ms": round(
                    mean(
                        output[
                            "retrieval_latency_ms"
                        ]
                        for output in technique_outputs
                    ),
                    3
                ),
                "chunking_seconds": (
                    chunk_data[
                        "chunking_seconds"
                    ]
                ),
                "indexing_seconds": (
                    chunk_data[
                        "indexing_seconds"
                    ]
                ),
            }
        )

    write_csv(
        RAW_DIR / "summary_metrics.csv",
        summary_rows,
        [
            "technique",
            "group",
            "chunks",
            "avg_chunk_length_chars",
            "mean_top_1_cosine",
            "mean_at_k_cosine",
            "recall_at_k",
            "mean_retrieval_latency_ms",
            "chunking_seconds",
            "indexing_seconds",
        ]
    )

    finished_at = datetime.now().astimezone()

    #Save basic run metadata
    run_metadata = {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "elapsed_seconds": (
            finished_at
            - started_at
        ).total_seconds(),
        "embedding_model": EMBED_MODEL_NAME,
        "generation_model": None,
        "document_count": len(documents),
        "question_count": len(questions),
        "top_k": arguments.top_k,
        "include_tuned": (
            arguments.include_tuned
        ),
        "techniques": [
            technique["name"]
            for technique in techniques
        ],
    }

    save_json(
        run_metadata,
        RAW_DIR / "run_metadata.json"
    )

    print()
    print(
        "=" * 100
    )
    print(
        f"JSONL saved to: {jsonl_path}"
    )
    print(
        "Summary saved to: "
        f"{RAW_DIR / 'summary_metrics.csv'}"
    )
    print(
        "Experiment finished:",
        finished_at.isoformat(
            timespec="seconds"
        )
    )
    print(
        "Total elapsed time:",
        f"{run_metadata['elapsed_seconds']:.1f} seconds"
    )
    print(
        "=" * 100
    )


if __name__ == "__main__":
    main()