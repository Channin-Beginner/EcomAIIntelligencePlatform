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

router = APIRouter(prefix="/home", tags=["admin-home"])


# --- Brand ---
@router.get("/brand/list")
def home_brand_list(
    brandName: str | None = None,
    recommendStatus: int | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if brandName:
        conditions.append("brand_name LIKE :brandName")
        params["brandName"] = f"%{brandName}%"
    if recommendStatus is not None:
        conditions.append("recommend_status = :recommendStatus")
        params["recommendStatus"] = recommendStatus
    return success(
        paginate(db, "sms_home_brand", " AND ".join(conditions), params, pageNum, pageSize, "sort DESC, id ASC")
    )


@router.post("/brand/create")
def home_brand_create(body: list[dict], db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    for item in body:
        insert_from_body(db, "sms_home_brand", item)
    db.commit()
    return success(len(body))


@router.post("/brand/delete")
def home_brand_delete(ids: str = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    id_list = parse_ids(ids)
    execute(db, f"DELETE FROM sms_home_brand WHERE id IN ({in_ids_sql(id_list)})")
    db.commit()
    return success(len(id_list))


@router.post("/brand/update/recommendStatus")
def home_brand_recommend_status(
    ids: str = Query(...),
    recommendStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(db, "sms_home_brand", parse_ids(ids), "recommend_status", recommendStatus)
    db.commit()
    return success(count)


@router.post("/brand/update/sort/{id}")
def home_brand_sort(
    id: int, sort: int = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    execute(db, "UPDATE sms_home_brand SET sort = :sort WHERE id = :id", {"sort": sort, "id": id})
    db.commit()
    return success(1)


# --- New product ---
@router.get("/newProduct/list")
def home_new_product_list(
    productName: str | None = None,
    recommendStatus: int | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if productName:
        conditions.append("product_name LIKE :productName")
        params["productName"] = f"%{productName}%"
    if recommendStatus is not None:
        conditions.append("recommend_status = :recommendStatus")
        params["recommendStatus"] = recommendStatus
    return success(
        paginate(db, "sms_home_new_product", " AND ".join(conditions), params, pageNum, pageSize, "sort DESC, id ASC")
    )


@router.post("/newProduct/create")
def home_new_product_create(body: list[dict], db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    for item in body:
        insert_from_body(db, "sms_home_new_product", item)
    db.commit()
    return success(len(body))


@router.post("/newProduct/delete")
def home_new_product_delete(ids: str = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    id_list = parse_ids(ids)
    execute(db, f"DELETE FROM sms_home_new_product WHERE id IN ({in_ids_sql(id_list)})")
    db.commit()
    return success(len(id_list))


@router.post("/newProduct/update/recommendStatus")
def home_new_product_recommend_status(
    ids: str = Query(...),
    recommendStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(db, "sms_home_new_product", parse_ids(ids), "recommend_status", recommendStatus)
    db.commit()
    return success(count)


@router.post("/newProduct/update/sort/{id}")
def home_new_product_sort(
    id: int, sort: int = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    execute(db, "UPDATE sms_home_new_product SET sort = :sort WHERE id = :id", {"sort": sort, "id": id})
    db.commit()
    return success(1)


# --- Recommend product ---
@router.get("/recommendProduct/list")
def home_recommend_product_list(
    productName: str | None = None,
    recommendStatus: int | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if productName:
        conditions.append("product_name LIKE :productName")
        params["productName"] = f"%{productName}%"
    if recommendStatus is not None:
        conditions.append("recommend_status = :recommendStatus")
        params["recommendStatus"] = recommendStatus
    return success(
        paginate(
            db,
            "sms_home_recommend_product",
            " AND ".join(conditions),
            params,
            pageNum,
            pageSize,
            "sort DESC, id ASC",
        )
    )


@router.post("/recommendProduct/create")
def home_recommend_product_create(body: list[dict], db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    for item in body:
        insert_from_body(db, "sms_home_recommend_product", item)
    db.commit()
    return success(len(body))


@router.post("/recommendProduct/delete")
def home_recommend_product_delete(
    ids: str = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    id_list = parse_ids(ids)
    execute(db, f"DELETE FROM sms_home_recommend_product WHERE id IN ({in_ids_sql(id_list)})")
    db.commit()
    return success(len(id_list))


@router.post("/recommendProduct/update/recommendStatus")
def home_recommend_product_recommend_status(
    ids: str = Query(...),
    recommendStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(
        db, "sms_home_recommend_product", parse_ids(ids), "recommend_status", recommendStatus
    )
    db.commit()
    return success(count)


@router.post("/recommendProduct/update/sort/{id}")
def home_recommend_product_sort(
    id: int, sort: int = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    execute(db, "UPDATE sms_home_recommend_product SET sort = :sort WHERE id = :id", {"sort": sort, "id": id})
    db.commit()
    return success(1)


# --- Recommend subject ---
@router.get("/recommendSubject/list")
def home_recommend_subject_list(
    subjectName: str | None = None,
    recommendStatus: int | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if subjectName:
        conditions.append("subject_name LIKE :subjectName")
        params["subjectName"] = f"%{subjectName}%"
    if recommendStatus is not None:
        conditions.append("recommend_status = :recommendStatus")
        params["recommendStatus"] = recommendStatus
    return success(
        paginate(
            db,
            "sms_home_recommend_subject",
            " AND ".join(conditions),
            params,
            pageNum,
            pageSize,
            "sort DESC, id ASC",
        )
    )


@router.post("/recommendSubject/create")
def home_recommend_subject_create(body: list[dict], db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    for item in body:
        insert_from_body(db, "sms_home_recommend_subject", item)
    db.commit()
    return success(len(body))


@router.post("/recommendSubject/delete")
def home_recommend_subject_delete(
    ids: str = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    id_list = parse_ids(ids)
    execute(db, f"DELETE FROM sms_home_recommend_subject WHERE id IN ({in_ids_sql(id_list)})")
    db.commit()
    return success(len(id_list))


@router.post("/recommendSubject/update/recommendStatus")
def home_recommend_subject_recommend_status(
    ids: str = Query(...),
    recommendStatus: int = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    count = update_status_by_ids(
        db, "sms_home_recommend_subject", parse_ids(ids), "recommend_status", recommendStatus
    )
    db.commit()
    return success(count)


@router.post("/recommendSubject/update/sort/{id}")
def home_recommend_subject_sort(
    id: int, sort: int = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    execute(db, "UPDATE sms_home_recommend_subject SET sort = :sort WHERE id = :id", {"sort": sort, "id": id})
    db.commit()
    return success(1)


# --- Advertise ---
@router.get("/advertise/list")
def home_advertise_list(
    name: str | None = None,
    type: int | None = None,
    endTime: str | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
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
    if endTime:
        conditions.append("end_time <= :endTime")
        params["endTime"] = endTime
    return success(paginate(db, "sms_home_advertise", " AND ".join(conditions), params, pageNum, pageSize, "sort DESC, id ASC"))


@router.get("/advertise/{id}")
def home_advertise_get(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(get_by_id(db, "sms_home_advertise", id))


@router.post("/advertise/create")
def home_advertise_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    insert_from_body(db, "sms_home_advertise", body)
    db.commit()
    return success(1)


@router.post("/advertise/update/{id}")
def home_advertise_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "sms_home_advertise", id, body)
    db.commit()
    return success(1)


@router.post("/advertise/delete")
def home_advertise_delete(ids: str = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    id_list = parse_ids(ids)
    execute(db, f"DELETE FROM sms_home_advertise WHERE id IN ({in_ids_sql(id_list)})")
    db.commit()
    return success(len(id_list))


@router.post("/advertise/update/status/{id}")
def home_advertise_status(
    id: int, status: int = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    execute(db, "UPDATE sms_home_advertise SET status = :status WHERE id = :id", {"status": status, "id": id})
    db.commit()
    return success(1)
