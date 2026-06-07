from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.common.auth import get_current_member
from app.common.response import success, validate_failed
from app.database import execute, fetch_all, fetch_one, get_db
from app.portal.event_log import log_event

router = APIRouter(prefix="/member/collection", tags=["portal-collection"])


class CollectionAddBody(BaseModel):
    productId: int


@router.get("/list")
def collection_list(db: Session = Depends(get_db), member: dict = Depends(get_current_member)):
    rows = fetch_all(
        db,
        """
        SELECT c.id, c.product_id, c.product_name, c.product_pic, c.product_sub_title,
               c.product_price, c.create_time,
               p.sale, p.stock, p.brand_name, p.product_category_name
        FROM ums_member_product_collection c
        LEFT JOIN pms_product p ON p.id = c.product_id AND p.delete_status = 0
        WHERE c.member_id = :mid
        ORDER BY c.create_time DESC
        """,
        {"mid": member["id"]},
    )
    items = []
    for row in rows:
        items.append(
            {
                "id": row["id"],
                "productId": row["product_id"],
                "productName": row["product_name"],
                "productPic": row["product_pic"],
                "productSubTitle": row["product_sub_title"],
                "productPrice": float(row["product_price"]) if row.get("product_price") is not None else None,
                "createTime": row["create_time"],
                "product": {
                    "id": row["product_id"],
                    "name": row["product_name"],
                    "pic": row["product_pic"],
                    "sub_title": row["product_sub_title"],
                    "price": float(row["product_price"]) if row.get("product_price") is not None else None,
                    "sale": row.get("sale"),
                    "stock": row.get("stock"),
                    "brand_name": row.get("brand_name"),
                    "product_category_name": row.get("product_category_name"),
                },
            }
        )
    return success(items)


@router.get("/status")
def collection_status(
    productId: int = Query(...),
    db: Session = Depends(get_db),
    member: dict = Depends(get_current_member),
):
    row = fetch_one(
        db,
        """
        SELECT id FROM ums_member_product_collection
        WHERE member_id = :mid AND product_id = :pid
        """,
        {"mid": member["id"], "pid": productId},
    )
    return success({"collected": bool(row)})


@router.post("/add")
def collection_add(
    body: CollectionAddBody,
    db: Session = Depends(get_db),
    member: dict = Depends(get_current_member),
):
    product = fetch_one(
        db,
        """
        SELECT id, name, pic, sub_title, price
        FROM pms_product
        WHERE id = :id AND publish_status = 1 AND delete_status = 0
        """,
        {"id": body.productId},
    )
    if not product:
        return validate_failed("商品不存在")

    existing = fetch_one(
        db,
        """
        SELECT id FROM ums_member_product_collection
        WHERE member_id = :mid AND product_id = :pid
        """,
        {"mid": member["id"], "pid": body.productId},
    )
    if existing:
        return success(1, "已在收藏夹")

    now = datetime.now()
    execute(
        db,
        """
        INSERT INTO ums_member_product_collection (
            member_id, product_id, product_name, product_pic, product_sub_title, product_price, create_time
        ) VALUES (
            :mid, :pid, :name, :pic, :sub, :price, :ct
        )
        """,
        {
            "mid": member["id"],
            "pid": body.productId,
            "name": product.get("name"),
            "pic": product.get("pic"),
            "sub": product.get("sub_title"),
            "price": product.get("price"),
            "ct": now,
        },
    )
    log_event(db, "fav", member_id=member["id"], product_id=body.productId, event_time=now)
    db.commit()
    return success(1, "收藏成功")


@router.post("/delete")
def collection_delete(
    productId: int = Query(...),
    db: Session = Depends(get_db),
    member: dict = Depends(get_current_member),
):
    execute(
        db,
        """
        DELETE FROM ums_member_product_collection
        WHERE member_id = :mid AND product_id = :pid
        """,
        {"mid": member["id"], "pid": productId},
    )
    db.commit()
    return success(1)
