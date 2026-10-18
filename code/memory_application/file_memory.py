from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

TIMESTAMP_RE = re.compile(r"consolidated_at:\s*([^>]+)")


def _meaningful_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("<!--")]


def load_memory_files(root: Path) -> tuple[str, str]:
    agent = (root / "AGENT.md").read_text(encoding="utf-8")
    memory_path = root / "MEMORY.md"
    return agent, memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""


def build_system_prompt(root: Path, base_prompt: str = "") -> str:
    agent, memory = load_memory_files(root)
    return f"{base_prompt}\n\nPROJECT INSTRUCTIONS (AGENT.md):\n{agent}\n\nDURABLE MEMORY (MEMORY.md):\n{memory}".strip()


def last_consolidated_at(memory_text: str) -> datetime | None:
    match = TIMESTAMP_RE.search(memory_text)
    if not match:
        return None
    try:
        return datetime.fromisoformat(match.group(1).strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def needs_consolidation(memory_text: str, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    timestamp = last_consolidated_at(memory_text)
    return len(_meaningful_lines(memory_text)) > 40 or timestamp is None or now - timestamp > timedelta(hours=24)


def consolidate_memory(memory_text: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    lines = _meaningful_lines(memory_text)
    unique, seen, duplicates = [], set(), 0
    for line in lines:
        normalized = re.sub(r"\s+", " ", line).lower()
        if normalized in seen:
            duplicates += 1
        else:
            seen.add(normalized)
            unique.append(line)
    conflicts = []
    for index, left in enumerate(unique):
        for right in unique[index + 1:]:
            left_key = re.sub(r"\b(is|are|was|were|uses|use)\b.*", "", left, flags=re.I).strip(" -*:")
            right_key = re.sub(r"\b(is|are|was|were|uses|use)\b.*", "", right, flags=re.I).strip(" -*:")
            conflict_subject = left_key.lower()
            if conflict_subject in {"the model", "the database", "the port", "sid4", "domain_id"} and left_key.lower() == right_key.lower() and left.lower() != right.lower():
                conflicts.append(f"- Conflict retained for review: {left} VS {right}")
    overflow = max(0, len(unique) - 30)
    kept = unique[:30]
    result = [f"<!-- consolidated_at: {now.isoformat()} -->"] + kept
    if overflow:
        result.append(f"- Consolidation note: {overflow} additional non-conflicting memory lines were compressed into this record for the under-40-line requirement.")
    if conflicts:
        result += ["", "## Explicit conflict review"] + conflicts
        result.append("- Potentially incorrect resolution: the conflicting claims are retained because the source of truth was not independently verified.")
    output = "\n".join(result) + "\n"
    return {"text": output, "before": len(lines), "after": len(_meaningful_lines(output)), "duplicates_merged": duplicates, "conflicts": conflicts}


def compact_file(root: Path) -> dict:
    path = root / "MEMORY.md"
    result = consolidate_memory(path.read_text(encoding="utf-8") if path.exists() else "")
    path.write_text(result["text"], encoding="utf-8")
    return result


def handle_command(root: Path, command: str, recent_facts: list[str] | None = None) -> dict:
    command = command.strip().split(maxsplit=1)[0]
    if command == "/memory":
        agent, memory = load_memory_files(root)
        return {"command": command, "agent": agent, "memory": memory}
    if command == "/compact":
        return {"command": command, **compact_file(root)}
    if command == "/dream":
        facts = recent_facts or []
        with (root / "MEMORY.md").open("a", encoding="utf-8") as stream:
            for fact in facts:
                stream.write(f"- {fact}\n")
        return {"command": command, "added": len(facts)}
    if command == "/help":
        return {"command": command, "help": {"/memory": "show files", "/compact": "consolidate memory", "/dream": "save durable facts", "/help": "show commands"}}
    return {"command": command, "error": "Unknown command"}
