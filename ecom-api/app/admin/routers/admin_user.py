from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.admin.helpers import delete_by_id, insert_from_body, paginate, parse_ids, serialize_rows, update_from_body
from app.common.auth import create_token, get_current_admin, hash_password, verify_password
from app.common.response import success
from app.config import get_settings
from app.database import execute, fetch_all, fetch_one, get_db

router = APIRouter(prefix="/admin", tags=["admin"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/login")
def admin_login(body: LoginBody, db: Session = Depends(get_db)):
    admin = fetch_one(
        db,
        "SELECT id, username, password, status FROM ums_admin WHERE username = :username",
        {"username": body.username},
    )
    if not admin or not verify_password(body.password, admin["password"]):
        return {"code": 404, "message": "用户名或密码错误", "data": None}
    if admin.get("status") != 1:
        return {"code": 500, "message": "帐号已被禁用", "data": None}
    token = create_token(admin["username"], "admin", admin["id"])
    settings = get_settings()
    return success({"token": token, "tokenHead": settings.token_head})


@router.get("/info")
def admin_info(
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_admin),
):
    roles = fetch_all(
        db,
        """
        SELECT r.name FROM ums_role r
        INNER JOIN ums_admin_role_relation arr ON r.id = arr.role_id
        WHERE arr.admin_id = :admin_id
        """,
        {"admin_id": current["id"]},
    )
    role_names = [r["name"] for r in roles]
    if not role_names:
        role_names = ["超级管理员"]

    menus = fetch_all(
        db,
        """
        SELECT DISTINCT m.id, m.parent_id, m.create_time, m.title, m.level, m.sort,
               m.name, m.icon, m.hidden
        FROM ums_menu m
        INNER JOIN ums_role_menu_relation rmr ON m.id = rmr.menu_id
        INNER JOIN ums_admin_role_relation arr ON rmr.role_id = arr.role_id
        WHERE arr.admin_id = :admin_id
        ORDER BY m.sort DESC, m.id ASC
        """,
        {"admin_id": current["id"]},
    )
    if not menus:
        menus = fetch_all(db, "SELECT * FROM ums_menu ORDER BY sort DESC, id ASC")

    return success(
        {
            "username": current["username"],
            "icon": current.get("icon"),
            "roles": role_names,
            "menus": serialize_rows(menus),
        }
    )


@router.post("/logout")
def admin_logout(_: dict = Depends(get_current_admin)):
    return success(None)


@router.get("/list")
def admin_list(
    keyword: str | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if keyword:
        conditions.append("(username LIKE :kw OR nick_name LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    page = paginate(
        db,
        "ums_admin",
        " AND ".join(conditions),
        params,
        pageNum,
        pageSize,
        "id ASC",
        columns="id, username, email, nick_name, note, create_time, login_time, status, icon",
    )
    return success(page)


@router.post("/register")
def admin_register(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    password = body.get("password")
    if password:
        body = dict(body)
        body["password"] = hash_password(password)
    body["create_time"] = datetime.now()
    insert_from_body(db, "ums_admin", body)
    db.commit()
    return success(1)


@router.post("/update/{id}")
def admin_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    if body.get("password"):
        body = dict(body)
        body["password"] = hash_password(body["password"])
    update_from_body(db, "ums_admin", id, body)
    db.commit()
    return success(1)


@router.post("/updateStatus/{id}")
def admin_update_status(
    id: int, status: int = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    execute(db, "UPDATE ums_admin SET status = :status WHERE id = :id", {"status": status, "id": id})
    db.commit()
    return success(1)


@router.post("/delete/{id}")
def admin_delete(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    execute(db, "DELETE FROM ums_admin_role_relation WHERE admin_id = :id", {"id": id})
    delete_by_id(db, "ums_admin", id)
    db.commit()
    return success(1)


@router.get("/role/{id}")
def admin_roles(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    rows = fetch_all(
        db,
        """
        SELECT r.* FROM ums_role r
        INNER JOIN ums_admin_role_relation arr ON r.id = arr.role_id
        WHERE arr.admin_id = :admin_id
        """,
        {"admin_id": id},
    )
    return success(serialize_rows(rows))


@router.post("/role/update")
def admin_role_update(
    adminId: int = Query(...),
    roleIds: str = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    id_list = parse_ids(roleIds)
    execute(db, "DELETE FROM ums_admin_role_relation WHERE admin_id = :admin_id", {"admin_id": adminId})
    for rid in id_list:
        execute(
            db,
            "INSERT INTO ums_admin_role_relation (admin_id, role_id) VALUES (:admin_id, :role_id)",
            {"admin_id": adminId, "role_id": rid},
        )
    db.commit()
    return success(len(id_list))
