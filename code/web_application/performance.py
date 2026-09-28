from contextvars import ContextVar

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import event
from sqlalchemy.orm import Session, joinedload

from database import db_session_basede26, get_db
from models import Trial, TrialDetail
from routers.auth import require_session


router = APIRouter(
    prefix="/api/performance",
    tags=["n-plus-one"],
)

query_counter = ContextVar(
    "query_counter",
    default=None,
)


@event.listens_for(
    db_session_basede26,
    "before_cursor_execute",
)
def count_sql_statements(
    conn,
    cursor,
    statement,
    parameters,
    context,
    executemany,
):
    counter = query_counter.get()

    if counter is not None:
        counter[0] += 1


@router.get("/naive")
def naive_trials(
    response: Response,
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    counter = [0]
    token = query_counter.set(counter)

    try:
        trials = (
            db.query(Trial)
            .order_by(Trial.id.asc())
            .limit(page_size)
            .all()
        )

        results = []

        for trial in trials:
            # Intentional N+1 query
            details = (
                db.query(TrialDetail)
                .filter(TrialDetail.trial_id == trial.id)
                .all()
            )

            results.append(
                {
                    "id": trial.id,
                    "brief_title": trial.brief_title,
                    "sponsor": trial.sponsor,
                    "details": [
                        {
                            "id": detail.id,
                            "detail": detail.detail,
                        }
                        for detail in details
                    ],
                }
            )

        response.headers["X-SQL-Statements"] = str(counter[0])
        return results

    finally:
        query_counter.reset(token)


@router.get("/fixed")
def fixed_trials(
    response: Response,
    page_size: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    counter = [0]
    token = query_counter.set(counter)

    try:
        trials = (
            db.query(Trial)
            .options(joinedload(Trial.details))
            .order_by(Trial.id.asc())
            .limit(page_size)
            .all()
        )

        results = [
            {
                "id": trial.id,
                "brief_title": trial.brief_title,
                "sponsor": trial.sponsor,
                "details": [
                    {
                        "id": detail.id,
                        "detail": detail.detail,
                    }
                    for detail in trial.details
                ],
            }
            for trial in trials
        ]

        response.headers["X-SQL-Statements"] = str(counter[0])
        return results

    finally:
        query_counter.reset(token)
