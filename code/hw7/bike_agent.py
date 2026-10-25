"""Framework-free core of the HW7 bike-share ReAct/MRKL exercise."""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import operator
import re
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def envelope(success: bool, data: Any = None, error: str | None = None, source: str | None = None) -> dict[str, Any]:
    return {"success": success, "data": data, "error": error, "source": source, "ts": datetime.now(timezone.utc).isoformat()}


def csv_sql(csv_path: str | Path, sql: str) -> dict[str, Any]:
    if not re.fullmatch(r"\s*SELECT\b[\s\S]*", sql, re.I) or ";" in sql.rstrip("; "):
        return envelope(False, error="only one read-only SELECT is allowed", source="uploaded.csv")
    path = Path(csv_path)
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        columns = list(rows[0]) if rows else []
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE trips (%s)" % ", ".join(f'"{c}" TEXT' for c in columns))
        connection.executemany("INSERT INTO trips VALUES (%s)" % ",".join("?" for _ in columns), [[r[c] for c in columns] for r in rows])
        result = [dict(row) for row in connection.execute(sql).fetchall()]
        return envelope(True, {"rows": result, "row_count": len(result)}, source="uploaded.csv")
    except (OSError, sqlite3.Error, KeyError) as exc:
        return envelope(False, error=f"csv_sql failed: {exc}", source="uploaded.csv")


def policy_retriever(url: str, query: str, k: int = 4) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            final_url = response.geturl()
            text = response.read().decode("utf-8", errors="ignore")
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        terms = {word.lower() for word in re.findall(r"\w+", query)}
        chunks = [text[i : i + 280] for i in range(0, len(text), 220)]
        scored = sorted(((len(terms & set(re.findall(r"\w+", chunk.lower()))), chunk) for chunk in chunks), reverse=True)
        passages = [{"text": chunk, "source": final_url, "score": score} for score, chunk in scored[:k] if score > 0]
        return envelope(True, {"passages": passages}, source=final_url)
    except Exception as exc:  # noqa: BLE001 - tool boundary
        return envelope(False, error=f"policy_retriever failed: {type(exc).__name__}", source=url)


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.USub: operator.neg}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression): return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS: return _OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS: return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    raise ValueError("unsupported expression")


def calculator(expression: str, units: str | None = None) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9+*/().\-\s]+", expression):
        return envelope(False, error="expression contains a non-whitelisted character")
    try:
        value = _safe_eval(ast.parse(expression, mode="eval"))
        if abs(value) > 1_000_000_000: raise ValueError("result exceeds safety limit")
        return envelope(True, {"value": value, "units": units})
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return envelope(False, error=f"calculator rejected expression: {exc}")


def snapshot_text(text: str, path: str | Path, source_url: str) -> dict[str, str]:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return {"source_url": source_url, "access_date_utc": datetime.now(timezone.utc).isoformat(), "sha256": digest, "path": str(output)}
