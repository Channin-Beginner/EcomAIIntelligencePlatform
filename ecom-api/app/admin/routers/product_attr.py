from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.helpers import (
    delete_by_id,
    get_by_id,
    in_ids_sql,
    insert_from_body,
    paginate,
    parse_ids,
    serialize_row,
    serialize_rows,
    update_from_body,
)
from app.common.auth import get_current_admin
from app.common.response import success
from app.database import execute, fetch_all, get_db

attr_router = APIRouter(prefix="/productAttribute", tags=["admin-product-attribute"])
cate_router = APIRouter(prefix="/productAttribute/category", tags=["admin-product-attribute-category"])


@cate_router.get("/list")
def category_list(
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    return success(paginate(db, "pms_product_attribute_category", "1=1", {}, pageNum, pageSize, "id ASC"))


@cate_router.get("/list/withAttr")
def category_list_with_attr(db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    categories = fetch_all(db, "SELECT * FROM pms_product_attribute_category ORDER BY id ASC")
    result = []
    for cat in categories:
        item = serialize_row(cat) or {}
        attrs = fetch_all(
            db,
            "SELECT * FROM pms_product_attribute WHERE product_attribute_category_id = :cid ORDER BY sort ASC, id ASC",
            {"cid": cat["id"]},
        )
        item["productAttributeList"] = serialize_rows(attrs)
        result.append(item)
    return success(result)


@cate_router.post("/create")
def category_create(
    name: str = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    execute(
        db,
        "INSERT INTO pms_product_attribute_category (name, attribute_count, param_count) VALUES (:name, 0, 0)",
        {"name": name},
    )
    db.commit()
    return success(1)


@cate_router.get("/delete/{id}")
def category_delete(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    delete_by_id(db, "pms_product_attribute_category", id)
    db.commit()
    return success(1)


@cate_router.post("/update/{id}")
def category_update(
    id: int,
    name: str = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    execute(db, "UPDATE pms_product_attribute_category SET name = :name WHERE id = :id", {"name": name, "id": id})
    db.commit()
    return success(1)


@attr_router.get("/attrInfo/{cate_id}")
def attr_info(cate_id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    rows = fetch_all(
        db,
        """
        SELECT pa.id AS attributeId, pac.id AS attributeCategoryId
        FROM pms_product_category_attribute_relation pcar
        LEFT JOIN pms_product_attribute pa ON pa.id = pcar.product_attribute_id
        LEFT JOIN pms_product_attribute_category pac ON pa.product_attribute_category_id = pac.id
        WHERE pcar.product_category_id = :cid
        """,
        {"cid": cate_id},
    )
    return success(serialize_rows(rows))


@attr_router.get("/list/{cid}")
def attr_list(
    cid: int,
    type: int = Query(...),
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    return success(
        paginate(
            db,
            "pms_product_attribute",
            "product_attribute_category_id = :cid AND type = :type",
            {"cid": cid, "type": type},
            pageNum,
            pageSize,
            "sort ASC, id ASC",
        )
    )


@attr_router.get("/{id}")
def attr_get(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(get_by_id(db, "pms_product_attribute", id))


@attr_router.post("/create")
def attr_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    cat_id = body.get("productAttributeCategoryId")
    insert_from_body(db, "pms_product_attribute", body)
    if cat_id:
        col = "attribute_count" if body.get("type") == 0 else "param_count"
        execute(
            db,
            f"UPDATE pms_product_attribute_category SET {col} = {col} + 1 WHERE id = :id",
            {"id": cat_id},
        )
    db.commit()
    return success(1)


@attr_router.post("/update/{id}")
def attr_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "pms_product_attribute", id, body)
    db.commit()
    return success(1)


@attr_router.post("/delete")
def attr_delete(ids: str = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    id_list = parse_ids(ids)
    if id_list:
        execute(db, f"DELETE FROM pms_product_attribute WHERE id IN ({in_ids_sql(id_list)})")
    db.commit()
    return success(len(id_list))
