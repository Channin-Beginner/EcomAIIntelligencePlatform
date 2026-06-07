from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.response import page_result, success
from app.database import fetch_all, fetch_one, get_db

router = APIRouter(prefix="/product", tags=["portal-product"])


def _serialize(row: dict) -> dict:
    out = dict(row)
    for key in ("price", "original_price", "promotion_price"):
        if out.get(key) is not None:
            out[key] = float(out[key])
    return out


@router.get("/detail/{product_id}")
def product_detail(product_id: int, db: Session = Depends(get_db)):
    product = fetch_one(
        db,
        "SELECT * FROM pms_product WHERE id = :id AND delete_status = 0",
        {"id": product_id},
    )
    if not product:
        return {"code": 404, "message": "商品不存在", "data": None}
    skus = fetch_all(db, "SELECT * FROM pms_sku_stock WHERE product_id = :id", {"id": product_id})
    brand = None
    if product.get("brand_id"):
        brand = fetch_one(db, "SELECT * FROM pms_brand WHERE id = :id", {"id": product["brand_id"]})
    for sku in skus:
        if sku.get("price") is not None:
            sku["price"] = float(sku["price"])
    return success({"product": _serialize(product), "skuStockList": skus, "brand": brand})


@router.get("/search")
def product_search(
    keyword: str | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(12, ge=1),
    db: Session = Depends(get_db),
):
    conditions = ["publish_status = 1", "delete_status = 0"]
    params: dict = {}
    if keyword:
        conditions.append("(name LIKE :kw OR keywords LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    where_sql = " AND ".join(conditions)
    total_row = fetch_one(db, f"SELECT COUNT(*) AS cnt FROM pms_product WHERE {where_sql}", params)
    total = int(total_row["cnt"]) if total_row else 0
    offset = (pageNum - 1) * pageSize
    params.update({"limit": pageSize, "offset": offset})
    rows = fetch_all(
        db,
        f"SELECT * FROM pms_product WHERE {where_sql} ORDER BY sort DESC LIMIT :limit OFFSET :offset",
        params,
    )
    return success(page_result([_serialize(r) for r in rows], total, pageNum, pageSize))
