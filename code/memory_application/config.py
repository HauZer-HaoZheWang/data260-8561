from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

PORT_BASE = int(os.getenv("PORT_BASE", "8461"))
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "s8561_doc")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen3:8b")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
SHORT_TERM_N = int(os.getenv("SHORT_TERM_N", "12"))
TOP_K = int(os.getenv("MEMORY_TOP_K", "5"))
SUMMARIZE_EVERY_USER_MSGS = int(os.getenv("SUMMARIZE_EVERY_USER_MSGS", "5"))
LIFETIME_EVERY_SESSION_SUMMARIES = int(
    os.getenv("LIFETIME_EVERY_SESSION_SUMMARIES", "3")
)
MEMORY_COMPRESSION = os.getenv("MEMORY_COMPRESSION", "0") == "1"
