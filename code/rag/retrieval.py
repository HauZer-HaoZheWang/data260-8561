"""Shared indexing and retrieval functions for HW3 Part 2.

This module builds an in-memory vector index and performs retrieval only.

It records store scores, manually calculated cosine similarities,
chunk lengths, source files, text previews, vector shapes, and latency.
"""

import json
import time
from pathlib import Path

import numpy as np
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import MetadataMode, QueryBundle
from llama_index.core.vector_stores import SimpleVectorStore

from pipeline import cosine_similarity


def build_index(
    nodes,
    embed_model
):
    """Build an in-memory vector index"""

    #Use a local in-memory vector store
    vector_store = SimpleVectorStore()

    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )

    #Measure indexing separately from retrieval
    start_time = time.perf_counter()

    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True
    )

    indexing_seconds = (
        time.perf_counter()
        - start_time
    )

    return index, indexing_seconds


def retrieve_query(
    index,
    embed_model,
    technique,
    question_id,
    question,
    expected_answer,
    expected_source,
    top_k=5
):
    """Retrieve top-k nodes and calculate retrieval measurements"""

    #Compute the query embedding once
    query_embedding = embed_model.get_query_embedding(
        question
    )

    query_array = np.asarray(
        query_embedding,
        dtype=float
    )

    #Pass the existing embedding to the retriever
    #Query embedding time is outside retrieval latency
    query_bundle = QueryBundle(
        query_str=question,
        embedding=query_embedding
    )

    retriever = index.as_retriever(
        similarity_top_k=top_k
    )

    #Measure the vector search time
    retrieval_start = time.perf_counter()

    retrieved_nodes = retriever.retrieve(
        query_bundle
    )

    retrieval_latency_ms = (
        time.perf_counter()
        - retrieval_start
    ) * 1000

    #Use only node text for manual cosine calculation
    chunk_texts = [
        item.node.get_content(
            metadata_mode=MetadataMode.NONE
        )
        for item in retrieved_nodes
    ]

    #Explicitly embed all returned chunks
    if chunk_texts:
        document_embeddings = (
            embed_model.get_text_embedding_batch(
                chunk_texts
            )
        )

        document_array = np.asarray(
            document_embeddings,
            dtype=float
        )
    else:
        document_embeddings = []

        document_array = np.empty(
            (
                0,
                len(query_embedding)
            ),
            dtype=float
        )

    results = []

    #Create one output row for every retrieved node
    for rank, (
        retrieved_item,
        chunk_text,
        document_embedding
    ) in enumerate(
        zip(
            retrieved_nodes,
            chunk_texts,
            document_embeddings
        ),
        start=1
    ):
        node = retrieved_item.node

        source_file = node.metadata.get(
            "source_file",
            ""
        )

        store_score = retrieved_item.score

        manual_cosine = cosine_similarity(
            query_embedding,
            document_embedding
        )

        #Sentence-window nodes store expanded context here
        window_text = node.metadata.get(
            "window",
            ""
        )

        #Keep terminal previews on one line
        preview = " ".join(
            chunk_text.split()
        )[:160]

        window_preview = " ".join(
            window_text.split()
        )[:160]

        results.append(
            {
                "rank": rank,
                "source_file": source_file,
                "store_score": (
                    float(store_score)
                    if store_score is not None
                    else None
                ),
                "cosine_similarity": manual_cosine,
                "chunk_length": len(chunk_text),
                "chunk_text": chunk_text,
                "preview": preview,
                "window_length": len(window_text),
                "window_text": window_text,
                "window_preview": window_preview,
                "matches_expected_source": (
                    source_file
                    == expected_source
                ),
            }
        )

    #Recall is one when the expected source appears in top-k
    recall_at_k = int(
        any(
            result["matches_expected_source"]
            for result in results
        )
    )

    cosine_values = [
        result["cosine_similarity"]
        for result in results
    ]

    #Use the largest manual cosine in the returned top-k
    top_1_cosine = (
        max(cosine_values)
        if cosine_values
        else 0.0
    )

    mean_cosine = (
        float(
            np.mean(
                cosine_values
            )
        )
        if cosine_values
        else 0.0
    )

    output = {
        "technique": technique,
        "question_id": question_id,
        "question": question,
        "expected_answer": expected_answer,
        "expected_source": expected_source,
        "top_k": top_k,
        "embedding_model": (
            "sentence-transformers/all-MiniLM-L6-v2"
        ),
        "query_embedding_dimension": len(
            query_embedding
        ),
        "query_embedding_first_8": [
            float(value)
            for value in query_embedding[:8]
        ],
        "query_vector_shape": list(
            query_array.shape
        ),
        "document_vectors_shape": list(
            document_array.shape
        ),
        "retrieval_latency_ms": (
            retrieval_latency_ms
        ),
        "top_1_cosine": top_1_cosine,
        "mean_at_k_cosine": mean_cosine,
        "recall_at_k": recall_at_k,
        "results": results,
    }

    print_retrieval_output(
        output
    )

    return output


def print_retrieval_output(
    output
):
    """Print one readable retrieval result table"""

    print()
    print(
        "=" * 100
    )

    print(
        f"Technique: {output['technique']}"
    )

    print(
        f"Question: {output['question_id']} - "
        f"{output['question']}"
    )

    print(
        f"Expected source: "
        f"{output['expected_source']}"
    )

    print(
        f"Query embedding dimension: "
        f"{output['query_embedding_dimension']}"
    )

    print(
        "Query embedding first 8 values: "
        f"{output['query_embedding_first_8']}"
    )

    print(
        f"Query vector shape: "
        f"{tuple(output['query_vector_shape'])}"
    )

    print(
        f"Document vectors shape: "
        f"{tuple(output['document_vectors_shape'])}"
    )

    print(
        f"Retrieval latency: "
        f"{output['retrieval_latency_ms']:.3f} ms"
    )

    print(
        f"Recall@{output['top_k']}: "
        f"{output['recall_at_k']}"
    )

    print(
        "-" * 100
    )

    print(
        f"{'Rank':<6}"
        f"{'Store':<12}"
        f"{'Cosine':<12}"
        f"{'Length':<10}"
        f"{'Source':<22}"
        f"Preview"
    )

    print(
        "-" * 100
    )

    for result in output["results"]:
        store_score = result[
            "store_score"
        ]

        if store_score is None:
            store_text = "None"
        else:
            store_text = (
                f"{store_score:.6f}"
            )

        print(
            f"{result['rank']:<6}"
            f"{store_text:<12}"
            f"{result['cosine_similarity']:<12.6f}"
            f"{result['chunk_length']:<10}"
            f"{result['source_file']:<22}"
            f"{result['preview']}"
        )

        #Print the expanded context for sentence-window
        if (
            output["technique"]
            == "sentence_window"
            and result["window_preview"]
        ):
            print(
                f"{'':<62}"
                f"Window: "
                f"{result['window_preview']}"
            )

    print(
        "-" * 100
    )

    print(
        f"Top-1 cosine: "
        f"{output['top_1_cosine']:.6f}"
    )

    print(
        f"Mean@{output['top_k']} cosine: "
        f"{output['mean_at_k_cosine']:.6f}"
    )

    print(
        "=" * 100
    )


def save_json(
    output,
    output_path
):
    """Save one result as formatted JSON"""

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path.write_text(
        json.dumps(
            output,
            indent=2
        ),
        encoding="utf-8"
    )