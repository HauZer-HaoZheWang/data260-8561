from datetime import datetime, timedelta
import secrets

from sqlalchemy.orm import Session

from models import SessionToken


SESSION_TTL_MINUTES = 30


def create_session(db: Session, user_id: int) -> SessionToken:
    # Generate an opaque random token
    token = secrets.token_urlsafe(48)

    session_row = SessionToken(
        id=token,
        user_id=user_id,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow()
        + timedelta(minutes=SESSION_TTL_MINUTES),
    )

    db.add(session_row)
    db.commit()
    db.refresh(session_row)

    return session_row


def get_session(db: Session, token: str | None):
    if not token:
        return None

    session_row = (
        db.query(SessionToken)
        .filter(SessionToken.id == token)
        .first()
    )

    if not session_row:
        return None

    if session_row.expires_at <= datetime.utcnow():
        db.delete(session_row)
        db.commit()
        return None

    return session_row


def delete_session(db: Session, token: str | None) -> None:
    if not token:
        return

    session_row = (
        db.query(SessionToken)
        .filter(SessionToken.id == token)
        .first()
    )

    if session_row:
        db.delete(session_row)
        db.commit()
