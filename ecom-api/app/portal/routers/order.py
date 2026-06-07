import random
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.common.auth import get_current_member
from app.common.response import page_result, success
from app.database import execute, fetch_all, fetch_one, get_db

router = APIRouter(prefix="/order", tags=["portal-order"])


class OrderParam(BaseModel):
    memberReceiveAddressId: int
    couponId: int | None = None
    payType: int = 1
    cartIds: list[int] = []


def _gen_order_sn() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))


def _serialize_order(row: dict) -> dict:
    out = dict(row)
    for key in ("total_amount", "pay_amount", "freight_amount"):
        if out.get(key) is not None:
            out[key] = float(out[key])
    for key in ("create_time", "payment_time"):
        if out.get(key) is not None:
            out[key] = str(out[key])
    return out


@router.post("/generateConfirmOrder")
def generate_confirm_order(
    cart_ids: list[int] = Body(...),
    db: Session = Depends(get_db),
    member: dict = Depends(get_current_member),
):
    if not cart_ids:
        return {"code": 404, "message": "购物车为空", "data": None}
    id_list = ",".join(str(i) for i in cart_ids)
    cart_items = fetch_all(
        db,
        f"""
        SELECT * FROM oms_cart_item
        WHERE id IN ({id_list}) AND member_id = :mid AND delete_status = 0
        """,
        {"mid": member["id"]},
    )
    calc_amount = {"totalAmount": 0, "freightAmount": 0, "payAmount": 0}
    for item in cart_items:
        calc_amount["totalAmount"] += float(item["price"]) * item["quantity"]
    calc_amount["payAmount"] = calc_amount["totalAmount"] + calc_amount["freightAmount"]
    address_list = fetch_all(
        db,
        "SELECT * FROM ums_member_receive_address WHERE member_id = :mid",
        {"mid": member["id"]},
    )
    return success(
        {
            "cartPromotionItemList": cart_items,
            "memberReceiveAddressList": address_list,
            "couponHistoryDetailList": [],
            "integrationConsumeSetting": None,
            "calcAmount": calc_amount,
        }
    )


@router.post("/generateOrder")
def generate_order(
    body: OrderParam,
    db: Session = Depends(get_db),
    member: dict = Depends(get_current_member),
):
    address = fetch_one(
        db,
        "SELECT * FROM ums_member_receive_address WHERE id = :id AND member_id = :mid",
        {"id": body.memberReceiveAddressId, "mid": member["id"]},
    )
    if not address:
        return {"code": 404, "message": "收货地址不存在", "data": None}

    cart_items = []
    if body.cartIds:
        id_list = ",".join(str(i) for i in body.cartIds)
        cart_items = fetch_all(
            db,
            f"""
            SELECT * FROM oms_cart_item
            WHERE id IN ({id_list}) AND member_id = :mid AND delete_status = 0
            """,
            {"mid": member["id"]},
        )
    if not cart_items:
        return {"code": 404, "message": "购物车为空", "data": None}

    total = sum(float(i["price"]) * i["quantity"] for i in cart_items)
    now = datetime.now()
    order_sn = _gen_order_sn()
    execute(
        db,
        """
        INSERT INTO oms_order (
            member_id, order_sn, create_time, member_username, total_amount, pay_amount,
            freight_amount, pay_type, source_type, status, order_type,
            receiver_name, receiver_phone, receiver_post_code, receiver_province,
            receiver_city, receiver_region, receiver_detail_address, delete_status, confirm_status
        ) VALUES (
            :member_id, :order_sn, :create_time, :username, :total, :pay,
            0, :pay_type, 0, 0, 0,
            :rname, :rphone, :post, :prov, :city, :region, :detail, 0, 0
        )
        """,
        {
            "member_id": member["id"],
            "order_sn": order_sn,
            "create_time": now,
            "username": member["username"],
            "total": total,
            "pay": total,
            "pay_type": body.payType,
            "rname": address["name"],
            "rphone": address["phone_number"],
            "post": address.get("post_code"),
            "prov": address["province"],
            "city": address["city"],
            "region": address["region"],
            "detail": address["detail_address"],
        },
    )
    order_row = fetch_one(db, "SELECT LAST_INSERT_ID() AS id", {})
    order_id = order_row["id"]
    for item in cart_items:
        execute(
            db,
            """
            INSERT INTO oms_order_item (
                order_id, order_sn, product_id, product_pic, product_name,
                product_brand, product_sn, product_price, product_quantity,
                product_sku_id, product_sku_code, product_category_id
            ) VALUES (
                :oid, :osn, :pid, :pic, :pname,
                :brand, :sn, :price, :qty,
                :sku_id, :sku_code, :cate
            )
            """,
            {
                "oid": order_id,
                "osn": order_sn,
                "pid": item["product_id"],
                "pic": item.get("product_pic"),
                "pname": item.get("product_name"),
                "brand": item.get("product_brand"),
                "sn": item.get("product_sn"),
                "price": item["price"],
                "qty": item["quantity"],
                "sku_id": item.get("product_sku_id"),
                "sku_code": item.get("product_sku_code"),
                "cate": item.get("product_category_id"),
            },
        )
        execute(
            db,
            "UPDATE oms_cart_item SET delete_status = 1 WHERE id = :id",
            {"id": item["id"]},
        )
        execute(
            db,
            "UPDATE pms_product SET sale = IFNULL(sale, 0) + :qty WHERE id = :pid",
            {"qty": item["quantity"], "pid": item["product_id"]},
        )
    db.commit()
    return success({"order": {"id": order_id, "orderSn": order_sn}}, "下单成功")


@router.post("/paySuccess")
def pay_success(
    orderId: int,
    payType: int = 1,
    db: Session = Depends(get_db),
    member: dict = Depends(get_current_member),
):
    now = datetime.now()
    execute(
        db,
        """
        UPDATE oms_order SET status = 1, pay_type = :pt, payment_time = :ptm
        WHERE id = :id AND member_id = :mid
        """,
        {"pt": payType, "ptm": now, "id": orderId, "mid": member["id"]},
    )
    db.commit()
    return success(1, "支付成功")


@router.get("/list")
def order_list(
    status: int = -1,
    pageNum: int = 1,
    pageSize: int = 5,
    db: Session = Depends(get_db),
    member: dict = Depends(get_current_member),
):
    conditions = ["member_id = :mid", "delete_status = 0"]
    params: dict = {"mid": member["id"]}
    if status >= 0:
        conditions.append("status = :status")
        params["status"] = status
    where_sql = " AND ".join(conditions)
    total_row = fetch_one(db, f"SELECT COUNT(*) AS cnt FROM oms_order WHERE {where_sql}", params)
    total = int(total_row["cnt"]) if total_row else 0
    offset = (pageNum - 1) * pageSize
    params.update({"limit": pageSize, "offset": offset})
    orders = fetch_all(
        db,
        f"SELECT * FROM oms_order WHERE {where_sql} ORDER BY create_time DESC LIMIT :limit OFFSET :offset",
        params,
    )
    result_list = []
    for order in orders:
        items = fetch_all(db, "SELECT * FROM oms_order_item WHERE order_id = :id", {"id": order["id"]})
        for item in items:
            if item.get("product_price") is not None:
                item["product_price"] = float(item["product_price"])
        result_list.append({"order": _serialize_order(order), "orderItemList": items})
    return success(page_result(result_list, total, pageNum, pageSize))


@router.get("/detail/{order_id}")
def order_detail(order_id: int, db: Session = Depends(get_db), member: dict = Depends(get_current_member)):
    order = fetch_one(
        db,
        "SELECT * FROM oms_order WHERE id = :id AND member_id = :mid",
        {"id": order_id, "mid": member["id"]},
    )
    if not order:
        return {"code": 404, "message": "订单不存在", "data": None}
    items = fetch_all(db, "SELECT * FROM oms_order_item WHERE order_id = :id", {"id": order_id})
    return success({"order": _serialize_order(order), "orderItemList": items})
