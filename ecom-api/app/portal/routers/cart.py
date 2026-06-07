from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.common.auth import get_current_member
from app.common.response import success
from app.database import execute, fetch_all, fetch_one, get_db
from app.portal.event_log import log_event

router = APIRouter(prefix="/cart", tags=["portal-cart"])


class CartAddBody(BaseModel):
    productId: int
    productSkuId: int | None = None
    quantity: int = 1


@router.post("/add")
def cart_add(body: CartAddBody, db: Session = Depends(get_db), member: dict = Depends(get_current_member)):
    product = fetch_one(db, "SELECT * FROM pms_product WHERE id = :id", {"id": body.productId})
    if not product:
        return {"code": 404, "message": "商品不存在", "data": None}
    sku = None
    if body.productSkuId:
        sku = fetch_one(db, "SELECT * FROM pms_sku_stock WHERE id = :id", {"id": body.productSkuId})
    price = float(sku["price"]) if sku and sku.get("price") else float(product["price"] or 0)
    now = datetime.now()
    existing = fetch_one(
        db,
        """
        SELECT * FROM oms_cart_item
        WHERE member_id = :mid AND product_id = :pid AND delete_status = 0
        AND (product_sku_id = :skuid OR (product_sku_id IS NULL AND :skuid IS NULL))
        """,
        {"mid": member["id"], "pid": body.productId, "skuid": body.productSkuId},
    )
    if existing:
        execute(
            db,
            "UPDATE oms_cart_item SET quantity = quantity + :qty, modify_date = :md WHERE id = :id",
            {"qty": body.quantity, "md": now, "id": existing["id"]},
        )
        log_event(db, "cart", member_id=member["id"], product_id=body.productId, event_time=now)
        db.commit()
        return success(existing["id"])
    execute(
        db,
        """
        INSERT INTO oms_cart_item (
            product_id, product_sku_id, member_id, quantity, price, product_pic,
            product_name, product_sub_title, member_nickname, create_date, modify_date,
            delete_status, product_category_id, product_brand, product_sn
        ) VALUES (
            :product_id, :sku_id, :member_id, :quantity, :price, :pic,
            :name, :sub_title, :nickname, :cd, :md,
            0, :cate_id, :brand, :sn
        )
        """,
        {
            "product_id": body.productId,
            "sku_id": body.productSkuId,
            "member_id": member["id"],
            "quantity": body.quantity,
            "price": price,
            "pic": product.get("pic"),
            "name": product.get("name"),
            "sub_title": product.get("sub_title"),
            "nickname": member.get("nickname") or member["username"],
            "cd": now,
            "md": now,
            "cate_id": product.get("product_category_id"),
            "brand": None,
            "sn": product.get("product_sn"),
        },
    )
    log_event(db, "cart", member_id=member["id"], product_id=body.productId, event_time=now)
    db.commit()
    new_id = fetch_one(db, "SELECT LAST_INSERT_ID() AS id", {})
    return success(new_id["id"] if new_id else 1)


@router.get("/list")
def cart_list(db: Session = Depends(get_db), member: dict = Depends(get_current_member)):
    rows = fetch_all(
        db,
        "SELECT * FROM oms_cart_item WHERE member_id = :mid AND delete_status = 0 ORDER BY id DESC",
        {"mid": member["id"]},
    )
    for r in rows:
        if r.get("price") is not None:
            r["price"] = float(r["price"])
    return success(rows)


@router.get("/update/quantity")
def cart_update_quantity(
    id: int,
    quantity: int,
    db: Session = Depends(get_db),
    member: dict = Depends(get_current_member),
):
    execute(
        db,
        "UPDATE oms_cart_item SET quantity = :qty, modify_date = :md WHERE id = :id AND member_id = :mid",
        {"qty": quantity, "md": datetime.now(), "id": id, "mid": member["id"]},
    )
    db.commit()
    return success(1)


@router.post("/delete")
def cart_delete(ids: list[int], db: Session = Depends(get_db), member: dict = Depends(get_current_member)):
    if not ids:
        return success(0)
    id_list = ",".join(str(i) for i in ids)
    execute(
        db,
        f"UPDATE oms_cart_item SET delete_status = 1 WHERE id IN ({id_list}) AND member_id = :mid",
        {"mid": member["id"]},
    )
    db.commit()
    return success(len(ids))
