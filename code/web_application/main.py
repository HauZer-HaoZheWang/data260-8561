from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from database import Base, db_session_basede26, get_db
from models import Sponsor, Trial
from routers.auth import require_session, router as auth_router
from performance import router as performance_router
from schemas import (
    SponsorCreate,
    SponsorOut,
    SponsorUpdate,
    TrialCreate,
    TrialOut,
    TrialUpdate,
)


BASE_DIR = Path(__file__).resolve().parent
PORT_BASE = 8461

app = FastAPI(
    title="Clinical Trial API",
    version="2.0.0",
)

# Create missing tables without deleting existing data
Base.metadata.create_all(bind=db_session_basede26)

# MySQL-backed authentication routes
app.include_router(auth_router)
app.include_router(performance_router)

# Serve frontend files
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)


def commit_or_conflict(db: Session, message: str):
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=message) from error


def find_sponsor_or_404(db: Session, sponsor_id: int):
    sponsor = db.query(Sponsor).filter(Sponsor.id == sponsor_id).first()

    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor not found")

    return sponsor


def find_trial_or_404(db: Session, trial_id: int):
    trial = (
        db.query(Trial)
        .options(joinedload(Trial.sponsor_entity))
        .filter(Trial.id == trial_id)
        .first()
    )

    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")

    return trial


@app.get("/trials")
def trials_ui():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.post(
    "/api/sponsors",
    response_model=SponsorOut,
    status_code=201,
    tags=["sponsors"],
)
def create_sponsor(
    sponsor_data: SponsorCreate,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    sponsor = Sponsor(**sponsor_data.model_dump())
    db.add(sponsor)
    commit_or_conflict(db, "Sponsor email already exists")
    db.refresh(sponsor)
    return sponsor


@app.get(
    "/api/sponsors",
    response_model=list[SponsorOut],
    tags=["sponsors"],
)
def get_sponsors(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    return (
        db.query(Sponsor)
        .order_by(Sponsor.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@app.get(
    "/api/sponsors/{sponsor_id}/trials",
    response_model=list[TrialOut],
    tags=["sponsors"],
)
def get_sponsor_trials(
    sponsor_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    find_sponsor_or_404(db, sponsor_id)
    return (
        db.query(Trial)
        .options(joinedload(Trial.sponsor_entity))
        .filter(Trial.sponsor_id == sponsor_id)
        .order_by(Trial.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@app.get(
    "/api/sponsors/{sponsor_id}",
    response_model=SponsorOut,
    tags=["sponsors"],
)
def get_sponsor(
    sponsor_id: int,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    return find_sponsor_or_404(db, sponsor_id)


@app.put(
    "/api/sponsors/{sponsor_id}",
    response_model=SponsorOut,
    tags=["sponsors"],
)
def update_sponsor(
    sponsor_id: int,
    sponsor_data: SponsorUpdate,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    sponsor = find_sponsor_or_404(db, sponsor_id)

    for key, value in sponsor_data.model_dump().items():
        setattr(sponsor, key, value)

    commit_or_conflict(db, "Sponsor email already exists")
    db.refresh(sponsor)
    return sponsor


@app.delete(
    "/api/sponsors/{sponsor_id}",
    status_code=204,
    tags=["sponsors"],
)
def delete_sponsor(
    sponsor_id: int,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    sponsor = find_sponsor_or_404(db, sponsor_id)

    if db.query(Trial.id).filter(Trial.sponsor_id == sponsor_id).first():
        raise HTTPException(
            status_code=409,
            detail="Sponsor has associated trials and cannot be deleted",
        )

    db.delete(sponsor)
    commit_or_conflict(db, "Sponsor could not be deleted")
    return Response(status_code=204)


@app.get(
    "/api/trials",
    response_model=list[TrialOut],
    tags=["trials"],
)
def get_trials(
    q: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    query = db.query(Trial).options(joinedload(Trial.sponsor_entity))

    if q and q.strip():
        search_text = f"%{q.strip()}%"
        query = query.join(Trial.sponsor_entity).filter(
            (Trial.brief_title.ilike(search_text))
            | (Trial.nct_code.ilike(search_text))
            | (Sponsor.name.ilike(search_text))
        )

    return (
        query.order_by(Trial.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@app.get(
    "/api/trials/{trial_id}",
    response_model=TrialOut,
    tags=["trials"],
)
def get_trial(
    trial_id: int,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    return find_trial_or_404(db, trial_id)


@app.post(
    "/api/trials",
    response_model=TrialOut,
    status_code=201,
    tags=["trials"],
)
def create_trial(
    trial_data: TrialCreate,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    find_sponsor_or_404(db, trial_data.sponsor_id)
    trial = Trial(**trial_data.model_dump())

    db.add(trial)
    commit_or_conflict(db, "Trial NCT code already exists")
    db.refresh(trial)

    return trial


@app.put(
    "/api/trials/{trial_id}",
    response_model=TrialOut,
    tags=["trials"],
)
def update_trial(
    trial_id: int,
    trial_data: TrialUpdate,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    trial = find_trial_or_404(db, trial_id)
    find_sponsor_or_404(db, trial_data.sponsor_id)

    for key, value in trial_data.model_dump().items():
        setattr(trial, key, value)

    commit_or_conflict(db, "Trial NCT code already exists")
    db.refresh(trial)

    return trial


@app.delete(
    "/api/trials/{trial_id}",
    status_code=204,
    tags=["trials"],
)
def delete_trial(
    trial_id: int,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    trial = find_trial_or_404(db, trial_id)

    db.delete(trial)
    commit_or_conflict(db, "Trial could not be deleted")
    return Response(status_code=204)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": "mysql",
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=PORT_BASE,
    )
