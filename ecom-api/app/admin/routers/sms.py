from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.helpers import (
    delete_by_id,
    get_by_id,
    insert_from_body,
    keys_to_snake,
    paginate,
    parse_ids,
    serialize_rows,
    update_from_body,
)
from app.common.auth import get_current_admin
from app.common.response import success
from app.database import execute, fetch_all, get_db

coupon_router = APIRouter(tags=["admin-coupon"])
flash_router = APIRouter(prefix="/flash", tags=["admin-flash"])
flash_session_router = APIRouter(prefix="/flashSession", tags=["admin-flash-session"])
flash_product_router = APIRouter(prefix="/flashProductRelation", tags=["admin-flash-product"])


# --- Coupon ---
@coupon_router.get("/coupon/list")
def coupon_list(
    name: str | None = None,
    type: int | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if name:
        conditions.append("name LIKE :name")
        params["name"] = f"%{name}%"
    if type is not None:
        conditions.append("type = :type")
        params["type"] = type
    return success(
        paginate(
            db,
            "sms_coupon",
            " AND ".join(conditions),
            params,
            pageNum,
            pageSize,
            "id DESC",
            extra_decimal=("amount", "min_point"),
        )
    )


@coupon_router.get("/coupon/{id}")
def coupon_get(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    coupon = get_by_id(db, "sms_coupon", id, ("amount", "min_point"))
    if not coupon:
        return {"code": 404, "message": "优惠券不存在", "data": None}
    coupon["productRelationList"] = serialize_rows(
        fetch_all(db, "SELECT * FROM sms_coupon_product_relation WHERE coupon_id = :id", {"id": id})
    )
    coupon["productCategoryRelationList"] = serialize_rows(
        fetch_all(db, "SELECT * FROM sms_coupon_product_category_relation WHERE coupon_id = :id", {"id": id})
    )
    return success(coupon)


@coupon_router.post("/coupon/create")
def coupon_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    product_rel = body.pop("productRelationList", None) or body.pop("product_relation_list", None) or []
    cate_rel = body.pop("productCategoryRelationList", None) or body.pop("product_category_relation_list", None) or []
    coupon_id = insert_from_body(db, "sms_coupon", body)
    for row in product_rel:
        data = keys_to_snake(row)
        execute(
            db,
            "INSERT INTO sms_coupon_product_relation (coupon_id, product_id, product_name, product_sn) "
            "VALUES (:coupon_id, :product_id, :product_name, :product_sn)",
            {
                "coupon_id": coupon_id,
                "product_id": data.get("product_id"),
                "product_name": data.get("product_name"),
                "product_sn": data.get("product_sn"),
            },
        )
    for row in cate_rel:
        data = keys_to_snake(row)
        execute(
            db,
            "INSERT INTO sms_coupon_product_category_relation (coupon_id, product_category_id, product_category_name, parent_category_name) "
            "VALUES (:coupon_id, :product_category_id, :product_category_name, :parent_category_name)",
            {
                "coupon_id": coupon_id,
                "product_category_id": data.get("product_category_id"),
                "product_category_name": data.get("product_category_name"),
                "parent_category_name": data.get("parent_category_name"),
            },
        )
    db.commit()
    return success(1)


@coupon_router.post("/coupon/update/{id}")
def coupon_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    product_rel = body.pop("productRelationList", None) or []
    cate_rel = body.pop("productCategoryRelationList", None) or []
    update_from_body(db, "sms_coupon", id, body)
    execute(db, "DELETE FROM sms_coupon_product_relation WHERE coupon_id = :id", {"id": id})
    execute(db, "DELETE FROM sms_coupon_product_category_relation WHERE coupon_id = :id", {"id": id})
    for row in product_rel:
        data = keys_to_snake(row)
        execute(
            db,
            "INSERT INTO sms_coupon_product_relation (coupon_id, product_id, product_name, product_sn) "
            "VALUES (:coupon_id, :product_id, :product_name, :product_sn)",
            {
                "coupon_id": id,
                "product_id": data.get("product_id"),
                "product_name": data.get("product_name"),
                "product_sn": data.get("product_sn"),
            },
        )
    for row in cate_rel:
        data = keys_to_snake(row)
        execute(
            db,
            "INSERT INTO sms_coupon_product_category_relation (coupon_id, product_category_id, product_category_name, parent_category_name) "
            "VALUES (:coupon_id, :product_category_id, :product_category_name, :parent_category_name)",
            {
                "coupon_id": id,
                "product_category_id": data.get("product_category_id"),
                "product_category_name": data.get("product_category_name"),
                "parent_category_name": data.get("parent_category_name"),
            },
        )
    db.commit()
    return success(1)


@coupon_router.post("/coupon/delete/{id}")
def coupon_delete(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    execute(db, "DELETE FROM sms_coupon_product_relation WHERE coupon_id = :id", {"id": id})
    execute(db, "DELETE FROM sms_coupon_product_category_relation WHERE coupon_id = :id", {"id": id})
    delete_by_id(db, "sms_coupon", id)
    db.commit()
    return success(1)


@coupon_router.get("/couponHistory/list")
def coupon_history_list(
    couponId: int | None = None,
    useStatus: int | None = None,
    orderSn: str | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if couponId is not None:
        conditions.append("coupon_id = :couponId")
        params["couponId"] = couponId
    if useStatus is not None:
        conditions.append("use_status = :useStatus")
        params["useStatus"] = useStatus
    if orderSn:
        conditions.append("order_sn LIKE :orderSn")
        params["orderSn"] = f"%{orderSn}%"
    return success(paginate(db, "sms_coupon_history", " AND ".join(conditions), params, pageNum, pageSize, "id DESC"))


# --- Flash promotion ---
@flash_router.get("/list")
def flash_list(
    keyword: str | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if keyword:
        conditions.append("title LIKE :kw")
        params["kw"] = f"%{keyword}%"
    return success(paginate(db, "sms_flash_promotion", " AND ".join(conditions), params, pageNum, pageSize, "id DESC"))


@flash_router.post("/create")
def flash_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    insert_from_body(db, "sms_flash_promotion", body)
    db.commit()
    return success(1)


@flash_router.post("/update/{id}")
def flash_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "sms_flash_promotion", id, body)
    db.commit()
    return success(1)


@flash_router.post("/delete/{id}")
def flash_delete(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    delete_by_id(db, "sms_flash_promotion", id)
    db.commit()
    return success(1)


@flash_router.post("/update/status/{id}")
def flash_update_status(
    id: int, status: int = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    execute(db, "UPDATE sms_flash_promotion SET status = :status WHERE id = :id", {"status": status, "id": id})
    db.commit()
    return success(1)


# --- Flash session ---
@flash_session_router.get("/selectList")
def flash_session_select_list(db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    rows = fetch_all(db, "SELECT * FROM sms_flash_promotion_session ORDER BY start_time ASC, id ASC")
    return success(serialize_rows(rows))


@flash_session_router.get("/list")
def flash_session_list(
    flashPromotionId: int | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if flashPromotionId is not None:
        conditions.append("flash_promotion_id = :flashPromotionId")
        params["flashPromotionId"] = flashPromotionId
    return success(
        paginate(db, "sms_flash_promotion_session", " AND ".join(conditions), params, pageNum, pageSize, "start_time ASC")
    )


@flash_session_router.post("/create")
def flash_session_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    insert_from_body(db, "sms_flash_promotion_session", body)
    db.commit()
    return success(1)


@flash_session_router.post("/update/{id}")
def flash_session_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "sms_flash_promotion_session", id, body)
    db.commit()
    return success(1)


@flash_session_router.post("/delete/{id}")
def flash_session_delete(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    delete_by_id(db, "sms_flash_promotion_session", id)
    db.commit()
    return success(1)


@flash_session_router.post("/update/status/{id}")
def flash_session_update_status(
    id: int, status: int = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    execute(db, "UPDATE sms_flash_promotion_session SET status = :status WHERE id = :id", {"status": status, "id": id})
    db.commit()
    return success(1)


# --- Flash product relation ---
@flash_product_router.get("/list")
def flash_product_list(
    flashPromotionId: int | None = None,
    flashPromotionSessionId: int | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if flashPromotionId is not None:
        conditions.append("flash_promotion_id = :flashPromotionId")
        params["flashPromotionId"] = flashPromotionId
    if flashPromotionSessionId is not None:
        conditions.append("flash_promotion_session_id = :flashPromotionSessionId")
        params["flashPromotionSessionId"] = flashPromotionSessionId
    return success(
        paginate(
            db,
            "sms_flash_promotion_product_relation",
            " AND ".join(conditions),
            params,
            pageNum,
            pageSize,
            "sort ASC, id ASC",
            extra_decimal=("flash_promotion_price",),
        )
    )


@flash_product_router.post("/create")
def flash_product_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    insert_from_body(db, "sms_flash_promotion_product_relation", body)
    db.commit()
    return success(1)


@flash_product_router.post("/update/{id}")
def flash_product_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "sms_flash_promotion_product_relation", id, body)
    db.commit()
    return success(1)


@flash_product_router.post("/delete/{id}")
def flash_product_delete(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    delete_by_id(db, "sms_flash_promotion_product_relation", id)
    db.commit()
    return success(1)
