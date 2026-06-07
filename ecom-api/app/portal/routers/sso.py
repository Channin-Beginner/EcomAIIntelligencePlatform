from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.common.auth import create_token, get_current_member, hash_password, verify_password
from app.common.response import success, validate_failed
from app.config import get_settings
from app.database import execute, fetch_one, get_db

router = APIRouter(prefix="/sso", tags=["portal-sso"])


class LoginBody(BaseModel):
    username: str
    password: str


class RegisterBody(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=64)
    telephone: str | None = None
    nickname: str | None = None


@router.post("/register")
def member_register(body: RegisterBody, db: Session = Depends(get_db)):
    username = body.username.strip()
    if not username:
        return validate_failed("用户名不能为空")

    if fetch_one(db, "SELECT id FROM ums_member WHERE username = :username", {"username": username}):
        return validate_failed("用户名已存在")

    phone = body.telephone.strip() if body.telephone else None
    if phone and fetch_one(db, "SELECT id FROM ums_member WHERE phone = :phone", {"phone": phone}):
        return validate_failed("手机号已被注册")

    nickname = body.nickname.strip() if body.nickname else username
    now = datetime.now()
    execute(
        db,
        """
        INSERT INTO ums_member (
            member_level_id, username, password, nickname, phone, status,
            create_time, integration, growth
        ) VALUES (
            :level_id, :username, :password, :nickname, :phone, 1,
            :create_time, 0, 0
        )
        """,
        {
            "level_id": 4,
            "username": username,
            "password": hash_password(body.password),
            "nickname": nickname,
            "phone": phone,
            "create_time": now,
        },
    )
    db.commit()
    return success(None, "注册成功")


@router.post("/login")
def member_login(body: LoginBody, db: Session = Depends(get_db)):
    member = fetch_one(
        db,
        "SELECT id, username, password, status FROM ums_member WHERE username = :username",
        {"username": body.username},
    )
    if not member or not verify_password(body.password, member["password"]):
        return {"code": 404, "message": "用户名或密码错误", "data": None}
    token = create_token(member["username"], "member", member["id"])
    settings = get_settings()
    return success({"token": token, "tokenHead": settings.token_head})


@router.get("/info")
def member_info(member: dict = Depends(get_current_member)):
    return success(
        {
            "id": member["id"],
            "username": member["username"],
            "nickname": member.get("nickname"),
            "phone": member.get("phone"),
            "icon": member.get("icon"),
        }
    )
