from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.helpers import (
    delete_by_id,
    get_by_id,
    in_ids_sql,
    insert_from_body,
    paginate,
    parse_ids,
    serialize_rows,
    update_from_body,
    update_status_by_ids,
)
from app.common.auth import get_current_admin
from app.common.response import success
from app.database import execute, fetch_all, get_db

router = APIRouter(tags=["admin-order-misc"])


@router.get("/orderSetting/{id}")
def order_setting_get(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(get_by_id(db, "oms_order_setting", id))


@router.post("/orderSetting/update/{id}")
def order_setting_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "oms_order_setting", id, body)
    db.commit()
    return success(1)


@router.get("/returnApply/list")
def return_apply_list(
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    return success(
        paginate(
            db,
            "oms_order_return_apply",
            "1=1",
            {},
            pageNum,
            pageSize,
            "create_time DESC",
            extra_decimal=("product_price", "return_amount", "real_amount"),
        )
    )


@router.get("/returnApply/{id}")
def return_apply_get(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(get_by_id(db, "oms_order_return_apply", id, ("product_price", "return_amount", "real_amount")))


@router.post("/returnApply/delete")
def return_apply_delete(ids: str = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    id_list = parse_ids(ids)
    execute(db, f"DELETE FROM oms_order_return_apply WHERE id IN ({in_ids_sql(id_list)})")
    db.commit()
    return success(len(id_list))


@router.post("/returnApply/update/status/{id}")
def return_apply_update_status(
    id: int, status: int = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    execute(db, "UPDATE oms_order_return_apply SET status = :status WHERE id = :id", {"status": status, "id": id})
    db.commit()
    return success(1)


@router.get("/returnReason/list")
def return_reason_list(
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    return success(paginate(db, "oms_order_return_reason", "1=1", {}, pageNum, pageSize, "sort DESC, id ASC"))


@router.get("/returnReason/{id}")
def return_reason_get(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(get_by_id(db, "oms_order_return_reason", id))


@router.post("/returnReason/create")
def return_reason_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    insert_from_body(db, "oms_order_return_reason", body)
    db.commit()
    return success(1)


@router.post("/returnReason/update/{id}")
def return_reason_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "oms_order_return_reason", id, body)
    db.commit()
    return success(1)


@router.post("/returnReason/delete")
def return_reason_delete(ids: str = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    id_list = parse_ids(ids)
    execute(db, f"DELETE FROM oms_order_return_reason WHERE id IN ({in_ids_sql(id_list)})")
    db.commit()
    return success(len(id_list))


@router.post("/returnReason/update/status")
def return_reason_update_status(
    ids: str = Query(...),
    status: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(db, "oms_order_return_reason", parse_ids(ids), "status", status)
    db.commit()
    return success(count)


@router.get("/companyAddress/list")
def company_address_list(db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(serialize_rows(fetch_all(db, "SELECT * FROM oms_company_address ORDER BY id ASC")))
