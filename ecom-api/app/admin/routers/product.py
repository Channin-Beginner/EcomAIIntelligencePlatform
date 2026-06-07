from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.helpers import parse_ids, serialize_row, serialize_rows, update_status_by_ids
from app.admin.product_service import create_product, get_product_update_info, update_product
from app.common.auth import get_current_admin
from app.common.response import page_result, success
from app.database import execute, fetch_all, fetch_one, get_db

router = APIRouter(prefix="/product", tags=["admin-product"])

_PRODUCT_DECIMAL = ("price", "original_price", "promotion_price", "weight")


@router.get("/list")
def product_list(
    keyword: str | None = None,
    publishStatus: int | None = None,
    verifyStatus: int | None = None,
    productSn: str | None = None,
    productCategoryId: int | None = None,
    brandId: int | None = None,
    pageSize: int = Query(5, ge=1),
    pageNum: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["delete_status = 0"]
    params: dict = {}
    if keyword:
        conditions.append("(name LIKE :kw OR product_sn LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    if publishStatus is not None:
        conditions.append("publish_status = :publishStatus")
        params["publishStatus"] = publishStatus
    if verifyStatus is not None:
        conditions.append("verify_status = :verifyStatus")
        params["verifyStatus"] = verifyStatus
    if productSn:
        conditions.append("product_sn LIKE :productSn")
        params["productSn"] = f"%{productSn}%"
    if productCategoryId is not None:
        conditions.append("product_category_id = :productCategoryId")
        params["productCategoryId"] = productCategoryId
    if brandId is not None:
        conditions.append("brand_id = :brandId")
        params["brandId"] = brandId

    where_sql = " AND ".join(conditions)
    total_row = fetch_one(db, f"SELECT COUNT(*) AS cnt FROM pms_product WHERE {where_sql}", params)
    total = int(total_row["cnt"]) if total_row else 0
    offset = (pageNum - 1) * pageSize
    params.update({"limit": pageSize, "offset": offset})
    rows = fetch_all(
        db,
        f"""
        SELECT * FROM pms_product
        WHERE {where_sql}
        ORDER BY sort DESC, id DESC
        LIMIT :limit OFFSET :offset
        """,
        params,
    )
    items = serialize_rows(rows, _PRODUCT_DECIMAL)
    return success(page_result(items, total, pageNum, pageSize))


@router.get("/updateInfo/{id}")
def product_update_info(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    data = get_product_update_info(db, id)
    if not data:
        return {"code": 404, "message": "商品不存在", "data": None}
    return success(data)


@router.post("/create")
def product_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    create_product(db, body)
    db.commit()
    return success(1)


@router.post("/update/{id}")
def product_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_product(db, id, body)
    db.commit()
    return success(1)


@router.post("/update/publishStatus")
def update_publish_status(
    ids: str = Query(...),
    publishStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(db, "pms_product", parse_ids(ids), "publish_status", publishStatus)
    db.commit()
    return success(count)


@router.post("/update/newStatus")
def update_new_status(
    ids: str = Query(...),
    newStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(db, "pms_product", parse_ids(ids), "new_status", newStatus)
    db.commit()
    return success(count)


@router.post("/update/recommendStatus")
def update_recommend_status(
    ids: str = Query(...),
    recommendStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(db, "pms_product", parse_ids(ids), "recommand_status", recommendStatus)
    db.commit()
    return success(count)


@router.post("/update/deleteStatus")
def update_delete_status(
    ids: str = Query(...),
    deleteStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(db, "pms_product", parse_ids(ids), "delete_status", deleteStatus)
    db.commit()
    return success(count)
