from fastapi import APIRouter, Depends, HTTPException, Request, Response
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import LoginRequest, UserCreate, UserOut
from session_crud import (
    create_session,
    delete_session,
    get_session,
)


router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

SESSION_COOKIE_NAME = "session_id"
SESSION_MAX_AGE = 30 * 60


def require_session(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    session_row = get_session(db, token)

    if not session_row:
        raise HTTPException(
            status_code=401,
            detail="Login required",
        )

    return session_row


@router.post("/register", response_model=UserOut)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    password_hash = pwd_context.hash(payload.password)

    user = User(
        name=payload.name,
        email=str(payload.email),
        password_hash=password_hash,
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already exists",
        )

    return user


@router.post("/login")
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == str(payload.email))
        .first()
    )

    if not user or not pwd_context.verify(
        payload.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    session_row = create_session(
        db,
        user_id=user.id,
    )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_row.id,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
    )

    return {
        "message": "Logged in successfully",
        "user_id": user.id,
    }


@router.get("/me", response_model=UserOut)
def current_user(
    session_row=Depends(require_session),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.id == session_row.user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    return user


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    delete_session(db, token)

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
    )

    return {
        "message": "Logged out successfully",
    }
