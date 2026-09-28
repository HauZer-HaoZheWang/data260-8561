from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import Base, db_session_basede26, get_db
from models import Trial
from routers.auth import require_session, router as auth_router
from performance import router as performance_router
from schemas import TrialCreate, TrialOut, TrialUpdate


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


@app.get("/trials")
def trials_ui():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get(
    "/api/trials",
    response_model=list[TrialOut],
)
def get_trials(
    q: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    query = db.query(Trial)

    if q and q.strip():
        search_text = f"%{q.strip()}%"
        query = query.filter(
            (Trial.brief_title.ilike(search_text))
            | (Trial.sponsor.ilike(search_text))
        )

    return query.order_by(Trial.id.asc()).all()


@app.get(
    "/api/trials/{trial_id}",
    response_model=TrialOut,
)
def get_trial(
    trial_id: int,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    trial = (
        db.query(Trial)
        .filter(Trial.id == trial_id)
        .first()
    )

    if not trial:
        raise HTTPException(
            status_code=404,
            detail="Trial not found",
        )

    return trial


@app.post(
    "/api/trials",
    response_model=TrialOut,
    status_code=201,
)
def create_trial(
    trial_data: TrialCreate,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    trial = Trial(
        brief_title=trial_data.brief_title,
        sponsor=trial_data.sponsor,
    )

    db.add(trial)
    db.commit()
    db.refresh(trial)

    return trial


@app.put(
    "/api/trials/{trial_id}",
    response_model=TrialOut,
)
def update_trial(
    trial_id: int,
    trial_data: TrialUpdate,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    trial = (
        db.query(Trial)
        .filter(Trial.id == trial_id)
        .first()
    )

    if not trial:
        raise HTTPException(
            status_code=404,
            detail="Trial not found",
        )

    trial.brief_title = trial_data.brief_title
    trial.sponsor = trial_data.sponsor

    db.commit()
    db.refresh(trial)

    return trial


@app.delete("/api/trials/{trial_id}")
def delete_trial(
    trial_id: int,
    db: Session = Depends(get_db),
    _session=Depends(require_session),
):
    trial = (
        db.query(Trial)
        .filter(Trial.id == trial_id)
        .first()
    )

    if not trial:
        raise HTTPException(
            status_code=404,
            detail="Trial not found",
        )

    db.delete(trial)
    db.commit()

    return {
        "message": "Trial deleted successfully",
        "trial_id": trial_id,
    }


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
