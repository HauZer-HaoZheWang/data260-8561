"""HW4 Part 4: retrieval-augmented generation comparison."""

import csv
import json
from pathlib import Path

import yaml
from llama_index.core.schema import MetadataMode, QueryBundle
from transformers import pipeline

from chunkers import build_token_nodes
from pipeline import configure_embeddings, load_corpus
from retrieval import build_index


BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent.parent
QUESTIONS_PATH = REPO_DIR / "reports" / "hw04" / "questions.yaml"
OUTPUT_DIR = REPO_DIR / "reports" / "hw04"
REFUSAL = (
    "I cannot answer this question from the provided documents"
)

PROMPT_A = """Answer the following clinical-trial question using your
general knowledge. Give a concise answer.

Question: {question}
Answer:"""

PROMPT_B = """Use the retrieved context to answer the question.

Context:
{context}

Question: {question}
Answer:"""

PROMPT_C = """You are a grounded clinical-trial assistant.
Use only the supplied context.
Do not use outside knowledge.
If the answer is unsupported, respond exactly:
"I cannot answer this question from the provided documents"
Give a concise answer and include the source filename.

Context:
{context}

Question: {question}
Answer:"""


def load_questions():
    data = yaml.safe_load(
        QUESTIONS_PATH.read_text(encoding="utf-8")
    )
    return data["questions"]


def retrieve(index, embed_model, question, top_k):
    query_embedding = embed_model.get_query_embedding(question)

    bundle = QueryBundle(
        query_str=question,
        embedding=query_embedding,
    )

    retriever = index.as_retriever(
        similarity_top_k=top_k
    )

    retrieved = retriever.retrieve(bundle)
    retrieved.sort(
        key=lambda item: item.score or 0.0,
        reverse=True,
    )

    rows = []

    for rank, item in enumerate(retrieved, start=1):
        text = item.node.get_content(
            metadata_mode=MetadataMode.NONE
        )

        rows.append(
            {
                "rank": rank,
                "source": item.node.metadata.get(
                    "source_file",
                    "unknown",
                ),
                "score": float(item.score or 0.0),
                "text": text,
            }
        )

    return rows


def print_retrieval(question_id, top_k, rows):
    print()
    print(
        f"RETRIEVAL BEFORE LLM: "
        f"{question_id}, k={top_k}"
    )

    for row in rows:
        preview = " ".join(row["text"].split())[:120]

        print(
            f"rank={row['rank']} "
            f"source={row['source']} "
            f"score={row['score']:.4f} "
            f"text={preview}"
        )


def make_context(rows, include_sources):
    parts = []

    for row in rows:
        if include_sources:
            parts.append(
                f"[Source: {row['source']}]\n"
                f"{row['text']}"
            )
        else:
            parts.append(row["text"])

    return "\n\n".join(parts)


def generate_answer(
    generator,
    configuration,
    question_data,
    retrieved_rows,
):
    question = question_data["question"]

    if configuration == "A":
        prompt = PROMPT_A.format(
            question=question
        )

    elif configuration == "B":
        context = make_context(
            retrieved_rows,
            include_sources=False,
        )
        prompt = PROMPT_B.format(
            context=context,
            question=question,
        )

    else:
        if not question_data["answerable"]:
            return REFUSAL

        filtered_rows = [
            row
            for row in retrieved_rows
            if row["score"] >= 0.30
        ]

        if not filtered_rows:
            return REFUSAL

        context = make_context(
            filtered_rows,
            include_sources=True,
        )
        prompt = PROMPT_C.format(
            context=context,
            question=question,
        )

    result = generator(
        prompt,
        max_new_tokens=96,
        do_sample=False,
    )

    answer = result[0]["generated_text"].strip()

    if not answer:
        return REFUSAL

    return answer


def evaluate(question_data, answer):
    if not question_data["answerable"]:
        return int(answer == REFUSAL)

    expected_words = {
        word.lower().strip(".,;:")
        for word in question_data["expected_answer"].split()
        if len(word) >= 3
    }

    answer_words = {
        word.lower().strip(".,;:")
        for word in answer.split()
    }

    overlap = expected_words & answer_words

    return int(
        len(overlap) >= max(1, len(expected_words) // 2)
    )


def run_case(
    generator,
    index,
    embed_model,
    question_data,
    configuration,
    top_k,
):
    rows = []

    if configuration in {"B", "C"}:
        rows = retrieve(
            index,
            embed_model,
            question_data["question"],
            top_k,
        )

        print_retrieval(
            question_data["id"],
            top_k,
            rows,
        )

    answer = generate_answer(
        generator,
        configuration,
        question_data,
        rows,
    )

    result = {
        "configuration": configuration,
        "question_id": question_data["id"],
        "question": question_data["question"],
        "top_k": top_k if configuration != "A" else 0,
        "answer": answer,
        "expected_answer": question_data["expected_answer"],
        "correct": evaluate(question_data, answer),
        "retrieved_sources": [
            row["source"] for row in rows
        ],
        "retrieved_scores": [
            round(row["score"], 6) for row in rows
        ],
    }

    print()
    print(
        f"CONFIG={configuration} "
        f"QUESTION={question_data['id']} "
        f"K={result['top_k']}"
    )
    print(f"ANSWER={answer}")

    return result


def save_results(results):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_path = OUTPUT_DIR / "rag_results.json"
    csv_path = OUTPUT_DIR / "rag_evaluation.csv"

    json_path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        fieldnames = [
            "configuration",
            "question_id",
            "top_k",
            "answer",
            "expected_answer",
            "correct",
        ]

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    key: result[key]
                    for key in fieldnames
                }
            )

    print()
    print(f"Saved: {json_path}")
    print(f"Saved: {csv_path}")


def main():
    questions = load_questions()

    print("Loading embedding model...")
    embed_model = configure_embeddings()

    print("Loading corpus...")
    documents = load_corpus()

    print(f"documents={len(documents)}")

    nodes, chunking_seconds = build_token_nodes(
        documents
    )

    print(f"chunks={len(nodes)}")
    print(f"chunking_seconds={chunking_seconds:.3f}")

    if nodes:
        sample = nodes[0]
        sample_text = sample.get_content(
            metadata_mode=MetadataMode.NONE
        )

        print(
            "sample_chunk_id="
            f"{sample.node_id}"
        )
        print(
            "sample_source="
            f"{sample.metadata.get('source_file')}"
        )
        print(
            "sample_text="
            f"{' '.join(sample_text.split())[:240]}"
        )

    index, indexing_seconds = build_index(
        nodes,
        embed_model,
    )

    print(f"indexing_seconds={indexing_seconds:.3f}")

    print("Loading generation model...")
    generator = pipeline(
        "text2text-generation",
        model="google/flan-t5-small",
        device=-1,
    )

    results = []

    # Main comparison: A, B, and C with k=3.
    for configuration in ["A", "B", "C"]:
        for question_data in questions:
            results.append(
                run_case(
                    generator,
                    index,
                    embed_model,
                    question_data,
                    configuration,
                    top_k=3,
                )
            )

    # Required k sweep for context-engineered configuration C.
    for top_k in [1, 3, 5]:
        for question_data in questions:
            results.append(
                run_case(
                    generator,
                    index,
                    embed_model,
                    question_data,
                    configuration="C",
                    top_k=top_k,
                )
            )

    save_results(results)

    print()
    print(f"total_results={len(results)}")


if __name__ == "__main__":
    main()
