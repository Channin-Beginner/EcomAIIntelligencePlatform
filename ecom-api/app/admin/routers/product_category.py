from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.helpers import (
    delete_by_id,
    get_by_id,
    insert_from_body,
    paginate,
    parse_ids,
    serialize_row,
    serialize_rows,
    update_from_body,
    update_status_by_ids,
)
from app.common.auth import get_current_admin
from app.common.response import success
from app.database import fetch_all, get_db

router = APIRouter(prefix="/productCategory", tags=["admin-product-category"])


@router.get("/list/withChildren")
def list_with_children(db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    all_rows = fetch_all(db, "SELECT * FROM pms_product_category ORDER BY sort DESC, id ASC")
    by_parent: dict[int, list] = {}
    for row in all_rows:
        pid = int(row.get("parent_id") or 0)
        by_parent.setdefault(pid, []).append(serialize_row(row))
    result = []
    for item in by_parent.get(0, []):
        item["children"] = by_parent.get(item["id"], [])
        result.append(item)
    return success(result)


@router.get("/list/{parent_id}")
def list_by_parent(
    parent_id: int,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    return success(
        paginate(
            db,
            "pms_product_category",
            "parent_id = :parent_id",
            {"parent_id": parent_id},
            pageNum,
            pageSize,
            "sort DESC, id ASC",
        )
    )


@router.get("/{id}")
def get_category(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(get_by_id(db, "pms_product_category", id))


@router.post("/create")
def create_category(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    insert_from_body(db, "pms_product_category", body)
    db.commit()
    return success(1)


@router.post("/update/{id}")
def update_category(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "pms_product_category", id, body)
    db.commit()
    return success(1)


@router.post("/delete/{id}")
def delete_category(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    delete_by_id(db, "pms_product_category", id)
    db.commit()
    return success(1)


@router.post("/update/navStatus")
def update_nav_status(
    ids: str = Query(...),
    navStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(db, "pms_product_category", parse_ids(ids), "nav_status", navStatus)
    db.commit()
    return success(count)


@router.post("/update/showStatus")
def update_show_status(
    ids: str = Query(...),
    showStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(db, "pms_product_category", parse_ids(ids), "show_status", showStatus)
    db.commit()
    return success(count)
