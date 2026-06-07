from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import fetch_one, get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def create_token(subject: str, role: str, user_id: int) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_expire_seconds)
    payload = {"sub": subject, "role": role, "uid": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    settings = get_settings()
    if authorization.startswith(settings.token_head):
        return authorization[len(settings.token_head) :]
    return authorization


def get_current_admin(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> dict:
    token = extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="unauthorized") from None
    if payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="unauthorized")
    admin = fetch_one(
        db,
        "SELECT id, username, icon, status FROM ums_admin WHERE username = :username",
        {"username": payload["sub"]},
    )
    if not admin or admin.get("status") != 1:
        raise HTTPException(status_code=401, detail="unauthorized")
    return admin


def get_current_member(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> dict:
    token = extract_bearer(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="unauthorized") from None
    if payload.get("role") != "member":
        raise HTTPException(status_code=401, detail="unauthorized")
    member = fetch_one(
        db,
        "SELECT id, username, nickname, phone, icon, status FROM ums_member WHERE username = :username",
        {"username": payload["sub"]},
    )
    if not member or member.get("status") != 1:
        raise HTTPException(status_code=401, detail="unauthorized")
    return member


def get_optional_member(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> dict | None:
    try:
        return get_current_member(authorization, db)
    except HTTPException:
        return None
