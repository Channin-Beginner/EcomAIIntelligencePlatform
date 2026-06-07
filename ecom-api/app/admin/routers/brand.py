from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.helpers import (
    delete_by_id,
    get_by_id,
    insert_from_body,
    paginate,
    parse_ids,
    serialize_rows,
    update_from_body,
    update_status_by_ids,
)
from app.common.auth import get_current_admin
from app.common.response import success
from app.database import fetch_all, get_db

router = APIRouter(prefix="/brand", tags=["admin-brand"])


@router.get("/listAll")
def list_all(db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    rows = fetch_all(db, "SELECT * FROM pms_brand ORDER BY sort DESC, id ASC")
    return success(serialize_rows(rows))


@router.get("/list")
def list_brand(
    keyword: str | None = None,
    showStatus: int | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if keyword:
        conditions.append("name LIKE :kw")
        params["kw"] = f"%{keyword}%"
    if showStatus is not None:
        conditions.append("show_status = :showStatus")
        params["showStatus"] = showStatus
    return success(paginate(db, "pms_brand", " AND ".join(conditions), params, pageNum, pageSize, "sort DESC, id ASC"))


@router.get("/{id}")
def get_brand(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(get_by_id(db, "pms_brand", id))


@router.post("/create")
def create_brand(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    insert_from_body(db, "pms_brand", body)
    db.commit()
    return success(1)


@router.post("/update/{id}")
def update_brand(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "pms_brand", id, body)
    db.commit()
    return success(1)


@router.get("/delete/{id}")
def delete_brand(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    delete_by_id(db, "pms_brand", id)
    db.commit()
    return success(None)


@router.post("/update/showStatus")
def update_show_status(
    ids: str = Query(...),
    showStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(db, "pms_brand", parse_ids(ids), "show_status", showStatus)
    db.commit()
    return success(count)


@router.post("/update/factoryStatus")
def update_factory_status(
    ids: str = Query(...),
    factoryStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(db, "pms_brand", parse_ids(ids), "factory_status", factoryStatus)
    db.commit()
    return success(count)
