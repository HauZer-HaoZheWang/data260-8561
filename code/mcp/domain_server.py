"""MCP tools for the s8561 clinical-trial relational database."""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload


WEB_APPLICATION_DIR = Path(__file__).resolve().parents[1] / "web_application"
load_dotenv(WEB_APPLICATION_DIR / ".env")
if str(WEB_APPLICATION_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_APPLICATION_DIR))

from database import SessionLocal  # noqa: E402
from models import Sponsor, Trial  # noqa: E402


logger = logging.getLogger("s8561_domain")
if not logger.handlers:
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(stderr_handler)
logger.setLevel(logging.INFO)
logger.propagate = False

mcp = FastMCP("s8561-clinical-trials")

SessionFactory = Callable[[], Session]
NCT_PATTERN = re.compile(r"^NCT\d{8}$")


def envelope(
    *, ok: bool, data: Any = None, error: str | None = None
) -> dict[str, Any]:
    """Create the one response envelope shared by all domain tools."""
    return {"ok": ok, "data": data, "error": error}


def success(data: Any) -> dict[str, Any]:
    """Create a successful domain-tool response."""
    return envelope(ok=True, data=data, error=None)


def failure(message: str) -> dict[str, Any]:
    """Create a rejected or failed domain-tool response."""
    return envelope(ok=False, data=None, error=message)


def _database_failure(error: SQLAlchemyError) -> dict[str, Any]:
    logger.error("Database operation failed: %s", error)
    return failure("database operation failed; please try again")


def search_trials_data(
    query: str,
    limit: int = 10,
    *,
    session_factory: SessionFactory = SessionLocal,
) -> dict[str, Any]:
    """Implementation for searching trials, injectable for offline tests."""
    if not isinstance(query, str) or not query.strip():
        return failure("query must be a non-empty string")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 25:
        return failure("limit must be an integer between 1 and 25")

    clean_query = query.strip()
    match = f"%{clean_query}%"
    try:
        with session_factory() as session:
            statement = (
                select(Trial)
                .join(Trial.sponsor_entity)
                .options(selectinload(Trial.sponsor_entity))
                .where(
                    or_(
                        Trial.brief_title.ilike(match),
                        Trial.nct_code.ilike(match),
                        Sponsor.name.ilike(match),
                    )
                )
                .order_by(Trial.id)
                .limit(limit)
            )
            trials = session.scalars(statement).all()
            rows = [
                {
                    "id": trial.id,
                    "nct_code": trial.nct_code,
                    "brief_title": trial.brief_title,
                    "participant_count": trial.participant_count,
                    "sponsor_id": trial.sponsor_id,
                    "sponsor_name": trial.sponsor_entity.name,
                }
                for trial in trials
            ]
    except SQLAlchemyError as error:
        return _database_failure(error)

    return success(
        {
            "query": clean_query,
            "count": len(rows),
            "trials": rows,
            "message": None if rows else "no matches",
        }
    )


def get_trial_details_data(
    nct_code: str,
    *,
    session_factory: SessionFactory = SessionLocal,
) -> dict[str, Any]:
    """Implementation for one complete trial lookup."""
    if not isinstance(nct_code, str):
        return failure("nct_code must be a string in NCT######## format")
    clean_code = nct_code.strip().upper()
    if not NCT_PATTERN.fullmatch(clean_code):
        return failure("nct_code must match NCT########")

    try:
        with session_factory() as session:
            statement = (
                select(Trial)
                .options(
                    selectinload(Trial.sponsor_entity),
                    selectinload(Trial.details),
                )
                .where(Trial.nct_code == clean_code)
            )
            trial = session.scalar(statement)
            if trial is None:
                return failure(f"trial {clean_code} was not found")

            result = {
                "id": trial.id,
                "nct_code": trial.nct_code,
                "brief_title": trial.brief_title,
                "participant_count": trial.participant_count,
                "created_at": trial.created_at.isoformat(),
                "updated_at": trial.updated_at.isoformat(),
                "sponsor": {
                    "id": trial.sponsor_entity.id,
                    "name": trial.sponsor_entity.name,
                    "contact_name": trial.sponsor_entity.contact_name,
                    "email": trial.sponsor_entity.email,
                },
                "details": [detail.detail for detail in trial.details],
            }
    except SQLAlchemyError as error:
        return _database_failure(error)

    return success(result)


def summarize_sponsors_data(
    min_trials: int = 1,
    limit: int = 10,
    *,
    session_factory: SessionFactory = SessionLocal,
) -> dict[str, Any]:
    """Implementation for aggregate sponsor statistics."""
    if (
        isinstance(min_trials, bool)
        or not isinstance(min_trials, int)
        or not 1 <= min_trials <= 5000
    ):
        return failure("min_trials must be an integer between 1 and 5000")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        return failure("limit must be an integer between 1 and 50")

    trial_count = func.count(Trial.id)
    total_participants = func.coalesce(func.sum(Trial.participant_count), 0)
    average_participants = func.coalesce(func.avg(Trial.participant_count), 0)

    try:
        with session_factory() as session:
            statement = (
                select(
                    Sponsor.id,
                    Sponsor.name,
                    trial_count.label("trial_count"),
                    total_participants.label("total_participants"),
                    average_participants.label("average_participants"),
                )
                .join(Trial, Trial.sponsor_id == Sponsor.id)
                .group_by(Sponsor.id, Sponsor.name)
                .having(trial_count >= min_trials)
                .order_by(trial_count.desc(), Sponsor.name)
                .limit(limit)
            )
            rows = session.execute(statement).all()
            summaries = [
                {
                    "sponsor_id": row.id,
                    "sponsor_name": row.name,
                    "trial_count": int(row.trial_count),
                    "total_participants": int(row.total_participants),
                    "average_participants": round(float(row.average_participants), 2),
                }
                for row in rows
            ]
    except SQLAlchemyError as error:
        return _database_failure(error)

    return success(
        {
            "min_trials": min_trials,
            "count": len(summaries),
            "sponsors": summaries,
            "message": None if summaries else "no matches",
        }
    )


@mcp.tool()
def search_trials(query: str, limit: int = 10) -> dict[str, Any]:
    """Search trials by title, NCT code, or sponsor name."""
    return search_trials_data(query, limit)


@mcp.tool()
def get_trial_details(nct_code: str) -> dict[str, Any]:
    """Return one trial with its sponsor and detail records."""
    return get_trial_details_data(nct_code)


@mcp.tool()
def summarize_sponsors(min_trials: int = 1, limit: int = 10) -> dict[str, Any]:
    """Aggregate trial counts and participant totals by sponsor."""
    return summarize_sponsors_data(min_trials, limit)


if __name__ == "__main__":
    mcp.run(transport="stdio")
