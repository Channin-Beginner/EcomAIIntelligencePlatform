from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.helpers import keys_to_snake, serialize_rows, update_from_body
from app.common.auth import get_current_admin
from app.common.response import success
from app.database import execute, fetch_all, get_db

router = APIRouter(prefix="/sku", tags=["admin-sku"])


@router.get("/{pid}")
def sku_list(
    pid: int,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["product_id = :pid"]
    params: dict = {"pid": pid}
    if keyword:
        conditions.append("sku_code LIKE :kw")
        params["kw"] = f"%{keyword}%"
    rows = fetch_all(
        db,
        f"SELECT * FROM pms_sku_stock WHERE {' AND '.join(conditions)} ORDER BY id ASC",
        params,
    )
    return success(serialize_rows(rows, ("price", "promotion_price")))


@router.post("/update/{pid}")
def sku_update(
    pid: int,
    body: list[dict],
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    for item in body:
        row_id = item.get("id")
        if not row_id:
            continue
        data = keys_to_snake(item)
        data.pop("id", None)
        data.pop("product_id", None)
        if data:
            update_from_body(db, "pms_sku_stock", int(row_id), data)
    db.commit()
    return success(1)
