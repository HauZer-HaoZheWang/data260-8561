"""Pure-Python sandbox file tools and a conservative Bash safety gate."""
from __future__ import annotations

import difflib
import fnmatch
import glob
import os
import re
import shlex
import subprocess
from pathlib import Path


SAFE_PREFIXES = ("pwd", "ls", "find", "grep", "head", "tail", "cat", "wc", "python -m pytest")
DESTRUCTIVE_PATTERNS = (
    r"\brm\s+(-[rf]+\s+)?", r"\bsudo\b", r"\b(chmod|chown)\b", r"\bdd\s+", r"\b(mkfs|mount|umount)\b",
    r"\b(shutdown|reboot)\b", r"(^|\s)>\s*/", r"\btruncate\b", r"\bmkfifo\b",
)


def _inside(path: str | Path, root: str | Path) -> Path:
    base = Path(root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute(): candidate = base / candidate
    candidate = candidate.resolve()
    if candidate != base and base not in candidate.parents: raise ValueError("path escapes sandbox")
    return candidate


def read_file(path: str | Path, root: str | Path, max_lines: int | None = None) -> str:
    text = _inside(path, root).read_text(encoding="utf-8")
    return "\n".join(text.splitlines()[:max_lines]) if max_lines is not None else text


def write_file(path: str | Path, content: str, root: str | Path) -> str:
    target = _inside(path, root); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content, encoding="utf-8"); return str(target)


def edit_file(path: str | Path, old: str, new: str, root: str | Path) -> str:
    target = _inside(path, root); before = target.read_text(encoding="utf-8")
    if old not in before: raise ValueError("old text not found")
    after = before.replace(old, new, 1); target.write_text(after, encoding="utf-8")
    return "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=str(path), tofile=str(path)))


def glob_files(pattern: str, root: str | Path) -> list[str]:
    base = Path(root).resolve(); return [str(Path(p).resolve().relative_to(base)) for p in glob.glob(str(base / pattern), recursive=True) if Path(p).is_file()]


def search_in_files(query: str, root: str | Path, file_pattern: str = "**/*") -> list[dict[str, object]]:
    hits = []
    for relative in glob_files(file_pattern, root):
        path = _inside(relative, root)
        try: lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError: continue
        for number, line in enumerate(lines, 1):
            if query in line: hits.append({"file": relative, "line": number, "text": line})
    return hits


def is_destructive(command: str) -> bool:
    return any(re.search(pattern, command, re.I) for pattern in DESTRUCTIVE_PATTERNS)


def confirm_bash(command: str, auto_approve: bool = False, cwd: str | Path | None = None) -> dict[str, object]:
    command = command.strip()
    if not command: return {"allowed": False, "reason": "empty command"}
    if is_destructive(command) and not auto_approve: return {"allowed": False, "reason": "destructive command requires explicit confirmation"}
    if not any(command == prefix or command.startswith(prefix + " ") for prefix in SAFE_PREFIXES): return {"allowed": False, "reason": "command is not in SAFE_PREFIXES"}
    if is_destructive(command): return {"allowed": True, "reason": "explicit confirmation supplied"}
    return {"allowed": True, "reason": "safe read-only prefix"}


def bash(command: str, *, cwd: str | Path, auto_approve: bool = False) -> dict[str, object]:
    decision = confirm_bash(command, auto_approve=auto_approve, cwd=cwd)
    if not decision["allowed"]: return decision
    result = subprocess.run(shlex.split(command), cwd=cwd, capture_output=True, text=True, check=False)
    return {"allowed": True, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "reason": decision["reason"]}
