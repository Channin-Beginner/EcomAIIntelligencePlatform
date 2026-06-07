from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.response import page_result, success
from app.database import fetch_all, fetch_one, get_db

router = APIRouter(prefix="/home", tags=["portal-home"])

_PUBLISHED = "publish_status = 1 AND delete_status = 0"


def _product_row(row: dict) -> dict:
    out = dict(row)
    if out.get("price") is not None:
        out["price"] = float(out["price"])
    return out


def _category_ids(db: Session, root_id: int) -> list[int]:
    rows = fetch_all(
        db,
        """
        SELECT id FROM pms_product_category WHERE id = :root
        UNION
        SELECT id FROM pms_product_category WHERE parent_id = :root
        """,
        {"root": root_id},
    )
    ids = [int(r["id"]) for r in rows]
    return ids if ids else [root_id]


def _feed_where(tab: str, category_id: int | None, db: Session) -> tuple[str, str]:
    conditions = [_PUBLISHED]
    if category_id:
        ids = _category_ids(db, category_id)
        id_sql = ", ".join(str(i) for i in ids)
        conditions.append(f"product_category_id IN ({id_sql})")
    elif tab == "recommend":
        conditions.append("recommand_status = 1")
    elif tab == "new":
        conditions.append("(new_status = 1 OR id >= 1000)")

    order_map = {
        "hot": "sale DESC, sort DESC, id DESC",
        "new": "id DESC",
        "recommend": "sort DESC, sale DESC, id DESC",
        "all": "sale DESC, sort DESC, id DESC",
    }
    order_by = order_map.get(tab, order_map["all"])
    return " AND ".join(conditions), order_by


@router.get("/content")
def home_content(db: Session = Depends(get_db)):
    advertises = fetch_all(
        db,
        """
        SELECT id, name, type, pic, url, sort, status, note, start_time, end_time
        FROM sms_home_advertise WHERE status = 1 ORDER BY sort DESC LIMIT 5
        """,
    )
    brands = fetch_all(
        db,
        "SELECT b.* FROM pms_brand b INNER JOIN sms_home_brand hb ON b.id = hb.brand_id ORDER BY hb.sort DESC LIMIT 6",
    )
    hot = fetch_all(
        db,
        """
        SELECT p.* FROM pms_product p
        INNER JOIN sms_home_recommend_product hr ON p.id = hr.product_id
        WHERE p.publish_status = 1 AND p.delete_status = 0
        ORDER BY hr.sort DESC LIMIT 10
        """,
    )
    if not hot:
        hot = fetch_all(
            db,
            f"SELECT * FROM pms_product WHERE {_PUBLISHED} ORDER BY sale DESC LIMIT 10",
        )
    new_products = fetch_all(
        db,
        """
        SELECT p.* FROM pms_product p
        INNER JOIN sms_home_new_product hn ON p.id = hn.product_id
        WHERE p.publish_status = 1 AND p.delete_status = 0
        ORDER BY hn.sort DESC LIMIT 10
        """,
    )
    if not new_products:
        new_products = fetch_all(
            db,
            f"SELECT * FROM pms_product WHERE {_PUBLISHED} AND new_status = 1 ORDER BY id DESC LIMIT 10",
        )
    categories = fetch_all(
        db,
        """
        SELECT pc.id, pc.name, COUNT(DISTINCT p.id) AS product_count
        FROM pms_product_category pc
        LEFT JOIN pms_product_category sub ON sub.parent_id = pc.id
        INNER JOIN pms_product p ON (
                p.product_category_id = sub.id OR p.product_category_id = pc.id
            ) AND p.publish_status = 1 AND p.delete_status = 0
        WHERE pc.parent_id = 0 AND pc.show_status = 1
        GROUP BY pc.id, pc.name
        HAVING product_count > 0
        ORDER BY product_count DESC
        LIMIT 8
        """,
    )
    total_products = fetch_one(
        db,
        f"SELECT COUNT(*) AS cnt FROM pms_product WHERE {_PUBLISHED}",
    )
    return success(
        {
            "advertiseList": advertises,
            "brandList": brands,
            "hotProductList": [_product_row(p) for p in hot],
            "newProductList": [_product_row(p) for p in new_products],
            "categoryNavList": categories,
            "totalProductCount": int(total_products["cnt"]) if total_products else 0,
            "subjectList": [],
        }
    )


@router.get("/productFeed")
def product_feed(
    tab: str = Query("all", pattern="^(all|hot|new|recommend)$"),
    categoryId: int | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=60),
    db: Session = Depends(get_db),
):
    """Paginated home feed — powers 为你推荐 grid and category tabs."""
    if categoryId:
        tab = "all"
    where_sql, order_by = _feed_where(tab, categoryId, db)
    total_row = fetch_one(db, f"SELECT COUNT(*) AS cnt FROM pms_product WHERE {where_sql}")
    total = int(total_row["cnt"]) if total_row else 0
    offset = (pageNum - 1) * pageSize
    rows = fetch_all(
        db,
        f"""
        SELECT * FROM pms_product WHERE {where_sql}
        ORDER BY {order_by}
        LIMIT :limit OFFSET :offset
        """,
        {"limit": pageSize, "offset": offset},
    )
    return success(page_result([_product_row(r) for r in rows], total, pageNum, pageSize))


@router.get("/hotProductList")
def hot_product_list(pageNum: int = 1, pageSize: int = 20, db: Session = Depends(get_db)):
    offset = (pageNum - 1) * pageSize
    rows = fetch_all(
        db,
        """
        SELECT * FROM pms_product WHERE publish_status = 1 AND delete_status = 0
        ORDER BY sale DESC LIMIT :limit OFFSET :offset
        """,
        {"limit": pageSize, "offset": offset},
    )
    return success([_product_row(r) for r in rows])


@router.get("/newProductList")
def new_product_list(pageNum: int = 1, pageSize: int = 20, db: Session = Depends(get_db)):
    offset = (pageNum - 1) * pageSize
    rows = fetch_all(
        db,
        """
        SELECT * FROM pms_product WHERE publish_status = 1 AND delete_status = 0
        ORDER BY id DESC LIMIT :limit OFFSET :offset
        """,
        {"limit": pageSize, "offset": offset},
    )
    return success([_product_row(r) for r in rows])


@router.get("/recommendProductList")
def recommend_product_list(pageNum: int = 1, pageSize: int = 20, db: Session = Depends(get_db)):
    offset = (pageNum - 1) * pageSize
    rows = fetch_all(
        db,
        """
        SELECT * FROM pms_product WHERE publish_status = 1 AND recommand_status = 1 AND delete_status = 0
        ORDER BY sort DESC LIMIT :limit OFFSET :offset
        """,
        {"limit": pageSize, "offset": offset},
    )
    return success([_product_row(r) for r in rows])
