from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.helpers import in_ids_sql, keys_to_snake, parse_ids, serialize_row, serialize_rows
from app.common.auth import get_current_admin
from app.common.response import page_result, success
from app.database import execute, fetch_all, fetch_one, get_db

router = APIRouter(prefix="/order", tags=["admin-order"])

_ORDER_DECIMAL = (
    "total_amount",
    "pay_amount",
    "freight_amount",
    "promotion_amount",
    "integration_amount",
    "coupon_amount",
    "discount_amount",
)
_ITEM_DECIMAL = ("product_price", "product_real_price")


@router.get("/list")
def order_list(
    orderSn: str | None = None,
    status: int | None = None,
    pageSize: int = Query(5, ge=1),
    pageNum: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["delete_status = 0"]
    params: dict = {}
    if orderSn:
        conditions.append("order_sn LIKE :orderSn")
        params["orderSn"] = f"%{orderSn}%"
    if status is not None:
        conditions.append("status = :status")
        params["status"] = status
    where_sql = " AND ".join(conditions)
    total_row = fetch_one(db, f"SELECT COUNT(*) AS cnt FROM oms_order WHERE {where_sql}", params)
    total = int(total_row["cnt"]) if total_row else 0
    offset = (pageNum - 1) * pageSize
    params.update({"limit": pageSize, "offset": offset})
    rows = fetch_all(
        db,
        f"""
        SELECT * FROM oms_order WHERE {where_sql}
        ORDER BY create_time DESC LIMIT :limit OFFSET :offset
        """,
        params,
    )
    return success(page_result(serialize_rows(rows, _ORDER_DECIMAL), total, pageNum, pageSize))


@router.get("/{order_id}")
def order_detail(order_id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    order = fetch_one(db, "SELECT * FROM oms_order WHERE id = :id", {"id": order_id})
    if not order:
        return {"code": 404, "message": "订单不存在", "data": None}
    items = fetch_all(db, "SELECT * FROM oms_order_item WHERE order_id = :id", {"id": order_id})
    history = fetch_all(
        db,
        "SELECT * FROM oms_order_operate_history WHERE order_id = :id ORDER BY create_time DESC",
        {"id": order_id},
    )
    return success(
        {
            "order": serialize_row(order, _ORDER_DECIMAL),
            "orderItemList": serialize_rows(items, _ITEM_DECIMAL),
            "historyList": serialize_rows(history),
        }
    )


@router.post("/update/delivery")
def order_delivery(
    body: list[dict],
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = 0
    now = datetime.now()
    for item in body:
        order_id = item.get("orderId") or item.get("order_id")
        execute(
            db,
            """
            UPDATE oms_order SET status = 2, delivery_company = :company,
            delivery_sn = :sn, delivery_time = :dt
            WHERE id = :id
            """,
            {
                "company": item.get("deliveryCompany"),
                "sn": item.get("deliverySn"),
                "dt": now,
                "id": order_id,
            },
        )
        execute(
            db,
            """
            INSERT INTO oms_order_operate_history (order_id, operate_man, create_time, order_status, note)
            VALUES (:oid, 'admin', :ct, 2, '发货')
            """,
            {"oid": order_id, "ct": now},
        )
        count += 1
    db.commit()
    return success(count)


@router.post("/update/note")
def order_note(
    id: int,
    note: str,
    status: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    execute(db, "UPDATE oms_order SET note = :note, status = :status WHERE id = :id", {"note": note, "status": status, "id": id})
    db.commit()
    return success(1)


@router.post("/update/close")
def order_close(
    ids: str = Query(...),
    note: str = Query(""),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    id_list = parse_ids(ids)
    now = datetime.now()
    for oid in id_list:
        execute(
            db,
            "UPDATE oms_order SET status = 4, note = :note WHERE id = :id",
            {"note": note, "id": oid},
        )
        execute(
            db,
            """
            INSERT INTO oms_order_operate_history (order_id, operate_man, create_time, order_status, note)
            VALUES (:oid, 'admin', :ct, 4, :note)
            """,
            {"oid": oid, "ct": now, "note": note or "关闭订单"},
        )
    db.commit()
    return success(len(id_list))


@router.post("/delete")
def order_delete(ids: str = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    id_list = parse_ids(ids)
    execute(
        db,
        f"UPDATE oms_order SET delete_status = 1 WHERE id IN ({in_ids_sql(id_list)})",
    )
    db.commit()
    return success(len(id_list))


@router.post("/update/receiverInfo")
def order_receiver_info(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    data = keys_to_snake(body)
    order_id = data.pop("order_id", None)
    status = data.pop("status", None)
    if order_id is None:
        return {"code": 400, "message": "orderId required", "data": None}
    allowed = {
        "receiver_name",
        "receiver_phone",
        "receiver_post_code",
        "receiver_detail_address",
        "receiver_province",
        "receiver_city",
        "receiver_region",
    }
    data = {k: v for k, v in data.items() if k in allowed}
    if status is not None:
        data["status"] = status
    if not data:
        return success(0)
    sets = ", ".join(f"{k} = :{k}" for k in data.keys())
    data["id"] = order_id
    execute(db, f"UPDATE oms_order SET {sets} WHERE id = :id", data)
    db.commit()
    return success(1)


@router.post("/update/moneyInfo")
def order_money_info(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    data = keys_to_snake(body)
    order_id = data.get("order_id")
    if order_id is None:
        return {"code": 400, "message": "orderId required", "data": None}
    execute(
        db,
        """
        UPDATE oms_order SET freight_amount = :freight_amount, discount_amount = :discount_amount, status = :status
        WHERE id = :id
        """,
        {
            "freight_amount": data.get("freight_amount"),
            "discount_amount": data.get("discount_amount"),
            "status": data.get("status"),
            "id": order_id,
        },
    )
    db.commit()
    return success(1)
