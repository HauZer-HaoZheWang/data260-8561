"""Three chunking techniques compared in HW3 Part 2.

Each builder returns the generated nodes and chunking time.
Chunking time is measured separately from retrieval latency.

The main experiment compares token, semantic 95, and sentence-window.
Semantic 80 is an additional ablation experiment.
"""

import time

from llama_index.core.node_parser import (
    SemanticSplitterNodeParser,
    SentenceWindowNodeParser,
    TokenTextSplitter,
)


# MiniLM accepts 256 total sequence positions, including special tokens.
# TokenTextSplitter does not use exactly the same tokenizer as MiniLM's
# WordPiece tokenizer, so 256 is a near-limit target for visible chunk text,
# not a strict guarantee. LlamaIndex metadata may also make the actual
# embedding input longer than the visible text.
TOKEN_CHUNK_SIZE = 256
TOKEN_CHUNK_OVERLAP = 32

#Use 95 for the required main semantic experiment
SEMANTIC_BREAKPOINT_PERCENTILE = 95

#Use 80 as the initial tuned ablation setting
SEMANTIC_BREAKPOINT_PERCENTILE_TUNED = 80

#Compare each sentence with its immediate neighbor
SEMANTIC_BUFFER_SIZE = 1

#Keep three nearby sentences on each side
WINDOW_SIZE = 3


def build_token_nodes(
    documents
):
    """Build fixed token chunks with overlap"""

    splitter = TokenTextSplitter(
        chunk_size=TOKEN_CHUNK_SIZE,
        chunk_overlap=TOKEN_CHUNK_OVERLAP
    )

    start_time = time.perf_counter()

    nodes = splitter.get_nodes_from_documents(
        documents
    )

    elapsed_seconds = (
        time.perf_counter()
        - start_time
    )

    return nodes, elapsed_seconds


def build_semantic_nodes(
    documents,
    embed_model,
    percentile=None
):
    """Build chunks using embedding guided boundaries"""

    #Use the main experiment value when none is provided
    if percentile is None:
        percentile = SEMANTIC_BREAKPOINT_PERCENTILE

    #A lower value creates more and smaller semantic chunks
    splitter = SemanticSplitterNodeParser(
        buffer_size=SEMANTIC_BUFFER_SIZE,
        breakpoint_percentile_threshold=percentile,
        embed_model=embed_model
    )

    start_time = time.perf_counter()

    nodes = splitter.get_nodes_from_documents(
        documents
    )

    elapsed_seconds = (
        time.perf_counter()
        - start_time
    )

    return nodes, elapsed_seconds


def build_tuned_semantic_nodes(
    documents,
    embed_model
):
    """Build the additional tuned semantic ablation"""

    return build_semantic_nodes(
        documents=documents,
        embed_model=embed_model,
        percentile=(
            SEMANTIC_BREAKPOINT_PERCENTILE_TUNED
        )
    )


def build_sentence_window_nodes(
    documents
):
    """Build one node per sentence with a nearby text window"""

    splitter = SentenceWindowNodeParser.from_defaults(
        window_size=WINDOW_SIZE,
        window_metadata_key="window",
        original_text_metadata_key="original_sentence"
    )

    start_time = time.perf_counter()

    nodes = splitter.get_nodes_from_documents(
        documents
    )

    elapsed_seconds = (
        time.perf_counter()
        - start_time
    )

    return nodes, elapsed_seconds