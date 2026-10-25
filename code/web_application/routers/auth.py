"""JWT authentication and reader/writer/moderator authorization for HW7."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "s8561-hw7-development-secret")
JWT_TTL_SECONDS = 30 * 60


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def create_access_token(user: User) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": str(user.id), "username": user.username or user.email, "role": user.role or "reader", "exp": int(time.time()) + JWT_TTL_SECONDS}, separators=(",", ":")).encode())
    signature = _b64(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_access_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        expected = _b64(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if int(data.get("exp", 0)) <= int(time.time()):
            raise ValueError("token expired")
        return data
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {exc}") from exc


@router.post("/register", response_model=UserOut)
def register(payload: dict, db: Session = Depends(get_db)):
    username = payload.get("username") or str(payload.get("email", "")).split("@", 1)[0]
    user = User(name=payload["name"], username=username, email=payload["email"], password_hash=pwd_context.hash(payload["password"]), role=payload.get("role", "reader"))
    db.add(user)
    try:
        db.commit(); db.refresh(user)
    except IntegrityError as error:
        db.rollback(); raise HTTPException(status_code=409, detail="Username or email already exists") from error
    return user


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        fields = urllib.parse.parse_qs((await request.body()).decode())
        username = fields.get("username", fields.get("email", [""]))[0]
        password = fields.get("password", [""])[0]
    else:
        try:
            fields = await request.json()
        except (ValueError, json.JSONDecodeError):
            fields = {}
        username = fields.get("username", fields.get("email", ""))
        password = fields.get("password", "")
    user = db.query(User).filter((User.username == username) | (User.email == username)).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": create_access_token(user), "token_type": "bearer"}


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    authorization = request.headers.get("Authorization", "")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    claims = decode_access_token(authorization.split(" ", 1)[1].strip())
    user = db.query(User).filter(User.id == int(claims["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_role(*roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)):
        if (user.role or "reader") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return dependency


# Existing HW4/HW5 imports keep this name; it now means JWT authentication only.
require_session = get_current_user


@router.get("/me", response_model=UserOut)
def current_user(user: User = Depends(get_current_user)):
    return user
