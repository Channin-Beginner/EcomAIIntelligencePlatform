"""Product create/update helpers for admin API."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.admin.helpers import (
    get_by_id,
    insert_from_body,
    keys_to_snake,
    serialize_row,
    serialize_rows,
    update_from_body,
)
from app.database import execute, fetch_all, fetch_one

_RELATION_KEYS = {
    "productLadderList",
    "productFullReductionList",
    "memberPriceList",
    "skuStockList",
    "productAttributeValueList",
    "subjectProductRelationList",
    "prefrenceAreaProductRelationList",
    "cateParentId",
    "flashPromotionCount",
    "flashPromotionId",
    "flashPromotionPrice",
    "flashPromotionSort",
    "brandName",
    "productCategoryName",
}

_PRODUCT_DECIMAL = (
    "price",
    "original_price",
    "promotion_price",
    "weight",
)


def _extract_relations(body: dict) -> dict[str, list]:
    return {
        "ladders": body.get("productLadderList") or [],
        "reductions": body.get("productFullReductionList") or [],
        "member_prices": body.get("memberPriceList") or [],
        "skus": body.get("skuStockList") or [],
        "attr_values": body.get("productAttributeValueList") or [],
        "subjects": body.get("subjectProductRelationList") or [],
        "prefrence_areas": body.get("prefrenceAreaProductRelationList") or [],
    }


def _insert_rows(db: Session, table: str, product_id: int, rows: list[dict], exclude: set[str] | None = None):
    exclude = (exclude or {"id", "productId"}) | {"id", "product_id"}
    for row in rows:
        data = keys_to_snake(row)
        for key in list(data.keys()):
            if key in exclude:
                data.pop(key, None)
        data["product_id"] = product_id
        if not data:
            continue
        cols = ", ".join(data.keys())
        vals = ", ".join(f":{k}" for k in data.keys())
        execute(db, f"INSERT INTO {table} ({cols}) VALUES ({vals})", data)


def _delete_product_relations(db: Session, product_id: int):
    for table in (
        "pms_product_ladder",
        "pms_product_full_reduction",
        "pms_member_price",
        "pms_sku_stock",
        "pms_product_attribute_value",
        "cms_subject_product_relation",
        "cms_prefrence_area_product_relation",
    ):
        execute(db, f"DELETE FROM {table} WHERE product_id = :pid", {"pid": product_id})


def create_product(db: Session, body: dict) -> int:
    relations = _extract_relations(body)
    product_body = {k: v for k, v in body.items() if k not in _RELATION_KEYS}
    product_id = insert_from_body(db, "pms_product", product_body)
    _insert_rows(db, "pms_product_ladder", product_id, relations["ladders"])
    _insert_rows(db, "pms_product_full_reduction", product_id, relations["reductions"])
    _insert_rows(db, "pms_member_price", product_id, relations["member_prices"])
    _insert_rows(db, "pms_sku_stock", product_id, relations["skus"])
    _insert_rows(db, "pms_product_attribute_value", product_id, relations["attr_values"])
    for row in relations["subjects"]:
        sid = row.get("subjectId") or row.get("subject_id")
        if sid:
            execute(
                db,
                "INSERT INTO cms_subject_product_relation (subject_id, product_id) VALUES (:sid, :pid)",
                {"sid": sid, "pid": product_id},
            )
    for row in relations["prefrence_areas"]:
        aid = row.get("prefrenceAreaId") or row.get("prefrence_area_id")
        if aid:
            execute(
                db,
                "INSERT INTO cms_prefrence_area_product_relation (prefrence_area_id, product_id) VALUES (:aid, :pid)",
                {"aid": aid, "pid": product_id},
            )
    return product_id


def update_product(db: Session, product_id: int, body: dict) -> int:
    relations = _extract_relations(body)
    product_body = {k: v for k, v in body.items() if k not in _RELATION_KEYS}
    update_from_body(db, "pms_product", product_id, product_body)
    _delete_product_relations(db, product_id)
    _insert_rows(db, "pms_product_ladder", product_id, relations["ladders"])
    _insert_rows(db, "pms_product_full_reduction", product_id, relations["reductions"])
    _insert_rows(db, "pms_member_price", product_id, relations["member_prices"])
    _insert_rows(db, "pms_sku_stock", product_id, relations["skus"])
    _insert_rows(db, "pms_product_attribute_value", product_id, relations["attr_values"])
    for row in relations["subjects"]:
        sid = row.get("subjectId") or row.get("subject_id")
        if sid:
            execute(
                db,
                "INSERT INTO cms_subject_product_relation (subject_id, product_id) VALUES (:sid, :pid)",
                {"sid": sid, "pid": product_id},
            )
    for row in relations["prefrence_areas"]:
        aid = row.get("prefrenceAreaId") or row.get("prefrence_area_id")
        if aid:
            execute(
                db,
                "INSERT INTO cms_prefrence_area_product_relation (prefrence_area_id, product_id) VALUES (:aid, :pid)",
                {"aid": aid, "pid": product_id},
            )
    return product_id


def get_product_update_info(db: Session, product_id: int) -> dict | None:
    product = get_by_id(db, "pms_product", product_id, _PRODUCT_DECIMAL)
    if not product:
        return None
    cat = fetch_one(db, "SELECT parent_id FROM pms_product_category WHERE id = :id", {"id": product.get("productCategoryId")})
    if cat:
        product["cateParentId"] = cat.get("parent_id")
    product["productLadderList"] = serialize_rows(
        fetch_all(db, "SELECT * FROM pms_product_ladder WHERE product_id = :id", {"id": product_id}),
        ("price", "discount"),
    )
    product["productFullReductionList"] = serialize_rows(
        fetch_all(db, "SELECT * FROM pms_product_full_reduction WHERE product_id = :id", {"id": product_id}),
        ("full_price", "reduce_price"),
    )
    product["memberPriceList"] = serialize_rows(
        fetch_all(db, "SELECT * FROM pms_member_price WHERE product_id = :id", {"id": product_id}),
        ("member_price",),
    )
    product["skuStockList"] = serialize_rows(
        fetch_all(db, "SELECT * FROM pms_sku_stock WHERE product_id = :id", {"id": product_id}),
        ("price", "promotion_price"),
    )
    product["productAttributeValueList"] = serialize_rows(
        fetch_all(db, "SELECT * FROM pms_product_attribute_value WHERE product_id = :id", {"id": product_id}),
    )
    product["subjectProductRelationList"] = serialize_rows(
        fetch_all(db, "SELECT * FROM cms_subject_product_relation WHERE product_id = :id", {"id": product_id}),
    )
    product["prefrenceAreaProductRelationList"] = serialize_rows(
        fetch_all(db, "SELECT * FROM cms_prefrence_area_product_relation WHERE product_id = :id", {"id": product_id}),
    )
    product.setdefault("flashPromotionCount", 0)
    product.setdefault("flashPromotionId", 0)
    product.setdefault("flashPromotionPrice", 0)
    product.setdefault("flashPromotionSort", 0)
    return product
