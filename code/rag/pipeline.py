"""Shared building blocks for the HW3 retrieval comparison.

Embedding model: sentence-transformers/all-MiniLM-L6-v2
Embedding dimension: 384
Execution: local CPU or MPS
Experiment type: retrieval only

No generation model is used.
"""

from pathlib import Path

import numpy as np
from llama_index.core import Settings, SimpleDirectoryReader
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


#Get the code/rag folder
BASE_DIR = Path(__file__).resolve().parent

#Get the repository root folder
REPO_DIR = BASE_DIR.parent.parent

#Read rendered clinical trial documents from this folder
CORPUS_DIR = BASE_DIR / "corpus"

#Store required homework outputs here
REPORTS_DIR = REPO_DIR / "reports" / "hw03"

#Use one local embedding model for all three techniques
EMBED_MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"
)

#This model returns 384-dimensional vectors
EMBEDDING_DIMENSION = 384

#Use the personal configuration seed
SEED = 8561


def configure_embeddings() -> HuggingFaceEmbedding:
    """Configure the local embedding model for LlamaIndex"""

    #Set the NumPy seed for reproducibility
    np.random.seed(SEED)

    #Load the local Hugging Face embedding model
    embed_model = HuggingFaceEmbedding(
        model_name=EMBED_MODEL_NAME
    )

    #Prevent LlamaIndex from using OpenAI embeddings
    Settings.embed_model = embed_model

    #Disable text generation because this is retrieval only
    Settings.llm = None

    return embed_model


def load_corpus():
    """Read every text document and keep its source filename"""

    #Stop with a clear error if the corpus is missing
    if not CORPUS_DIR.exists():
        raise FileNotFoundError(
            f"Corpus folder not found: {CORPUS_DIR}"
        )

    corpus_files = sorted(
        CORPUS_DIR.glob("*.txt")
    )

    #The graded corpus should not be empty
    if not corpus_files:
        raise FileNotFoundError(
            f"No text files found in {CORPUS_DIR}"
        )

    #Read every rendered clinical trial document
    reader = SimpleDirectoryReader(
        input_dir=str(CORPUS_DIR),
        required_exts=[".txt"],
        filename_as_id=True
    )

    documents = reader.load_data()

    #Keep a clean filename for Recall@k scoring
    for document in documents:
        file_path = document.metadata.get(
            "file_path",
            document.doc_id
        )

        document.metadata["source_file"] = Path(
            file_path
        ).name

    #Keep document order stable across experiment runs
    documents.sort(
        key=lambda document: document.metadata.get(
            "source_file",
            ""
        )
    )

    return documents


def cosine_similarity(
    vector_a,
    vector_b
) -> float:
    """Calculate cosine similarity between two vectors"""

    #Convert both vectors into NumPy arrays
    array_a = np.asarray(
        vector_a,
        dtype=float
    )
    array_b = np.asarray(
        vector_b,
        dtype=float
    )

    #Both vectors must have the same shape
    if array_a.shape != array_b.shape:
        raise ValueError(
            "Vectors must have the same shape: "
            f"{array_a.shape} != {array_b.shape}"
        )

    denominator = (
        np.linalg.norm(array_a)
        * np.linalg.norm(array_b)
    )

    #Avoid division by zero
    if denominator == 0:
        return 0.0

    return float(
        np.dot(array_a, array_b)
        / denominator
    )