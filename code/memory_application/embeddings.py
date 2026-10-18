from __future__ import annotations

import hashlib
import math

import ollama

from .config import EMBED_MODEL


def _fallback_embedding(text: str, dimensions: int = 32) -> list[float]:
    return [((int.from_bytes(hashlib.sha256(f"{i}:{text}".encode()).digest()[:4], "big") / 2**32) * 2 - 1) for i in range(dimensions)]


def embed(text: str) -> list[float]:
    try:
        vector = ollama.embeddings(model=EMBED_MODEL, prompt=text).get("embedding") or []
        if vector:
            return [float(value) for value in vector]
    except Exception:
        pass
    return _fallback_embedding(text)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    left, right = left[:size], right[:size]
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(y * y for y in right))
    return sum(x * y for x, y in zip(left, right)) / denominator if size and denominator else 0.0
