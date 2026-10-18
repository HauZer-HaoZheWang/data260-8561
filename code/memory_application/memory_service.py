from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone

from pymongo.errors import PyMongoError

from .config import (
    LIFETIME_EVERY_SESSION_SUMMARIES,
    MEMORY_COMPRESSION,
    SHORT_TERM_N,
    SUMMARIZE_EVERY_USER_MSGS,
    TOP_K,
)
from .db import collection
from .embeddings import cosine_similarity, embed
from .model_adapter import ask


PRIMER = (
    "You are a careful clinical-trial assistant. Use supplied memory as context, "
    "do not invent trial facts, and clearly distinguish known facts from uncertainty."
)


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4) if text else 0


def _public_message(row: dict) -> dict:
    """Return a JSON-safe message for the chat response."""
    result = dict(row)
    if "_id" in result:
        result["_id"] = str(result["_id"])
    return result


def _message_docs(user_id: str, session_id: str, limit: int | None = None) -> list[dict]:
    query = {"user_id": user_id, "session_id": session_id}
    cursor = collection("messages").find(query).sort("created_at", -1)
    if limit:
        cursor = cursor.limit(limit)
    return list(reversed(list(cursor)))


def extract_facts(user_id: str, session_id: str, message: str) -> list[dict]:
    """Extract up to three short, user-stated facts without a second LLM call."""
    sentences = [item.strip() for item in re.split(r"[.!?\n]+", message) if item.strip()]
    candidates = sentences[:3]
    facts = []
    for sentence in candidates:
        fact = sentence[:240]
        importance = 0.8 if re.search(r"\b(I am|I use|my|must|always|never)\b", fact, re.I) else 0.5
        facts.append({
            "user_id": user_id,
            "session_id": session_id,
            "fact": fact,
            "importance": importance,
            "embedding": embed(fact),
            "created_at": datetime.now(timezone.utc),
        })
    if facts:
        collection("episodes").insert_many(facts)
    return facts


def retrieve_episodes(user_id: str, message: str) -> list[dict]:
    query_vector = embed(message)
    scored = []
    for episode in collection("episodes").find({"user_id": user_id}).sort("created_at", -1).limit(200):
        score = cosine_similarity(query_vector, episode.get("embedding", []))
        episode = dict(episode)
        episode.pop("embedding", None)
        episode.pop("_id", None)
        episode["similarity"] = round(score, 4)
        scored.append(episode)
    scored.sort(key=lambda row: (row["similarity"], row.get("importance", 0)), reverse=True)
    return scored[:TOP_K]


def _latest_summary(user_id: str, session_id: str | None, scope: str) -> dict | None:
    query = {"user_id": user_id, "scope": scope}
    if scope == "session":
        query["session_id"] = session_id
    else:
        query["session_id"] = None
    return collection("summaries").find_one(query, sort=[("created_at", -1)])


def _summary_text(user_id: str, session_id: str, messages: list[dict], scope: str) -> str:
    transcript = "\n".join(f"{row['role']}: {row['content']}" for row in messages)
    prompt = (
        "Summarize the following clinical-trial conversation into concise factual bullets. "
        "Keep user preferences, constraints, decisions, and unresolved questions.\n" + transcript
    )
    try:
        result = ask([{"role": "system", "content": "You create compact factual memory."}, {"role": "user", "content": prompt}])
        text = result.get("text", "").strip()
    except Exception:
        text = "\n".join(f"- {row['role']}: {row['content'][:160]}" for row in messages[-8:])
    collection("summaries").insert_one({
        "user_id": user_id,
        "session_id": session_id if scope == "session" else None,
        "scope": scope,
        "text": text or "No durable facts identified.",
        "created_at": datetime.now(timezone.utc),
    })
    return text


def maybe_update_summaries(user_id: str, session_id: str, user_count: int) -> dict:
    result = {"session_summary_updated": False, "lifetime_summary_updated": False}
    if user_count % SUMMARIZE_EVERY_USER_MSGS == 0:
        messages = _message_docs(user_id, session_id)
        _summary_text(user_id, session_id, messages, "session")
        result["session_summary_updated"] = True
        count = collection("summaries").count_documents({"user_id": user_id, "scope": "session"})
        if count % LIFETIME_EVERY_SESSION_SUMMARIES == 0:
            session_summaries = list(collection("summaries").find({"user_id": user_id, "scope": "session"}).sort("created_at", -1).limit(12))
            text = "\n".join(item.get("text", "") for item in reversed(session_summaries))
            _summary_text(user_id, session_id, [{"role": "memory", "content": text}], "user")
            result["lifetime_summary_updated"] = True
    return result


def build_prompt(user_id: str, session_id: str, message: str) -> tuple[str, dict, dict]:
    started = time.perf_counter()
    short_term = _message_docs(user_id, session_id, SHORT_TERM_N)
    if MEMORY_COMPRESSION and len(short_term) > 4:
        short_term = short_term[-4:]
    session_summary = _latest_summary(user_id, session_id, "session")
    lifetime_summary = _latest_summary(user_id, None, "user")
    episodes = retrieve_episodes(user_id, message)
    sections = {
        "primer": PRIMER,
        "long_term_summary": "\n".join(filter(None, [
            lifetime_summary.get("text") if lifetime_summary else "",
            session_summary.get("text") if session_summary else "",
        ])),
        "short_term_window": "\n".join(f"{row['role']}: {row['content']}" for row in short_term),
        "episodic_facts": "\n".join(f"- {row['fact']}" for row in episodes),
    }
    prompt = (
        f"SYSTEM PRIMER:\n{sections['primer']}\n\n"
        f"LONG-TERM SUMMARY:\n{sections['long_term_summary'] or '(none)'}\n\n"
        f"SHORT-TERM WINDOW:\n{sections['short_term_window'] or '(none)'}\n\n"
        f"EPISODIC FACTS:\n{sections['episodic_facts'] or '(none)'}\n\n"
        f"CURRENT USER MESSAGE:\n{message}"
    )
    metrics = {"component_tokens": {key: estimate_tokens(value) for key, value in sections.items()}, "assembly_ms": round((time.perf_counter() - started) * 1000, 2)}
    used = {
        "short_term_messages": [_public_message(row) for row in short_term],
        "session_summary": session_summary.get("text") if session_summary else None,
        "lifetime_summary": lifetime_summary.get("text") if lifetime_summary else None,
        "episodic_facts": episodes,
    }
    return prompt, used, metrics


def chat(user_id: str, session_id: str, message: str) -> dict:
    started = time.perf_counter()
    now = datetime.now(timezone.utc)
    collection("messages").insert_one({"user_id": user_id, "session_id": session_id, "role": "user", "content": message, "created_at": now})
    facts = extract_facts(user_id, session_id, message)
    prompt, used, metrics = build_prompt(user_id, session_id, message)
    result = ask([{"role": "system", "content": PRIMER}, {"role": "user", "content": prompt}])
    reply = result.get("text", "").strip() or "I could not generate a response."
    collection("messages").insert_one({"user_id": user_id, "session_id": session_id, "role": "assistant", "content": reply, "created_at": datetime.now(timezone.utc)})
    user_count = collection("messages").count_documents({"user_id": user_id, "session_id": session_id, "role": "user"})
    summary_result = maybe_update_summaries(user_id, session_id, user_count)
    metrics.update({
        "prompt_tokens": int(result.get("input_tokens", estimate_tokens(prompt))),
        "completion_tokens": int(result.get("output_tokens", estimate_tokens(reply))),
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "facts_saved": len(facts),
    })
    metrics["summary_updates"] = summary_result
    collection("memory_metrics").insert_one({"user_id": user_id, "session_id": session_id, "created_at": now, **metrics})
    return {"reply": reply, "memory_used": used, "metrics": metrics}


def memory_view(user_id: str) -> dict:
    messages = list(collection("messages").find({"user_id": user_id}).sort("created_at", -1).limit(16))
    for row in messages:
        row["_id"] = str(row["_id"])
    episodes = list(collection("episodes").find({"user_id": user_id}).sort("created_at", -1).limit(20))
    for row in episodes:
        row["_id"] = str(row["_id"])
        row.pop("embedding", None)
    session = collection("summaries").find_one({"user_id": user_id, "scope": "session"}, sort=[("created_at", -1)])
    lifetime = collection("summaries").find_one({"user_id": user_id, "scope": "user"}, sort=[("created_at", -1)])
    for row in (session, lifetime):
        if row:
            row["_id"] = str(row["_id"])
    return {"messages": messages, "latest_session_summary": session, "latest_lifetime_summary": lifetime, "episodes": episodes}


def aggregate_view(user_id: str) -> dict:
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "message_count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    counts = list(collection("messages").aggregate(pipeline))
    return {"daily_message_counts": [{"date": row["_id"], "message_count": row["message_count"]} for row in counts], "recent_summaries": memory_view(user_id)["latest_session_summary"]}

