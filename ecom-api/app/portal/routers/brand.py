from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.response import page_result, success
from app.database import fetch_all, fetch_one, get_db

router = APIRouter(prefix="/brand", tags=["portal-brand"])


@router.get("/recommendList")
def brand_recommend_list(db: Session = Depends(get_db)):
    rows = fetch_all(
        db,
        """
        SELECT b.* FROM pms_brand b
        INNER JOIN sms_home_brand hb ON b.id = hb.brand_id
        ORDER BY hb.sort DESC
        """,
    )
    if not rows:
        rows = fetch_all(db, "SELECT * FROM pms_brand WHERE show_status = 1 LIMIT 10")
    return success(rows)


@router.get("/detail/{brand_id}")
def brand_detail(brand_id: int, db: Session = Depends(get_db)):
    brand = fetch_one(db, "SELECT * FROM pms_brand WHERE id = :id", {"id": brand_id})
    return success(brand)


@router.get("/productList")
def brand_product_list(
    brandId: int,
    pageNum: int = 1,
    pageSize: int = 12,
    db: Session = Depends(get_db),
):
    total_row = fetch_one(
        db,
        """
        SELECT COUNT(*) AS cnt FROM pms_product
        WHERE brand_id = :bid AND publish_status = 1 AND delete_status = 0
        """,
        {"bid": brandId},
    )
    total = int(total_row["cnt"]) if total_row else 0
    offset = (pageNum - 1) * pageSize
    rows = fetch_all(
        db,
        """
        SELECT * FROM pms_product
        WHERE brand_id = :bid AND publish_status = 1 AND delete_status = 0
        ORDER BY sort DESC LIMIT :limit OFFSET :offset
        """,
        {"bid": brandId, "limit": pageSize, "offset": offset},
    )
    for r in rows:
        if r.get("price") is not None:
            r["price"] = float(r["price"])
    return success(page_result(rows, total, pageNum, pageSize))
