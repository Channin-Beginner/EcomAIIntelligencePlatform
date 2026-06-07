from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.helpers import paginate, serialize_rows
from app.common.auth import get_current_admin
from app.common.response import success
from app.database import fetch_all, get_db

router = APIRouter(tags=["admin-cms"])


@router.get("/subject/listAll")
def subject_list_all(db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    rows = fetch_all(db, "SELECT * FROM cms_subject ORDER BY id DESC")
    return success(serialize_rows(rows))


@router.get("/subject/list")
def subject_list(
    keyword: str | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if keyword:
        conditions.append("title LIKE :kw")
        params["kw"] = f"%{keyword}%"
    return success(paginate(db, "cms_subject", " AND ".join(conditions), params, pageNum, pageSize, "id DESC"))


@router.get("/prefrenceArea/listAll")
def prefrence_area_list_all(db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    rows = fetch_all(db, "SELECT * FROM cms_prefrence_area ORDER BY id ASC")
    return success(serialize_rows(rows))
