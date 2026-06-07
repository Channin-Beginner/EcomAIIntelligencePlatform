from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.auth import get_optional_member
from app.common.response import page_result, success
from app.database import get_db
from app.recommend.service import get_recommender

router = APIRouter(prefix="/recommend", tags=["portal-recommend"])


@router.get("/forYou")
def for_you_feed(
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=60),
    member: dict | None = Depends(get_optional_member),
    db: Session = Depends(get_db),
):
    """Paginated 为你推荐 feed — ItemCF scores descending, fallback to hot sale."""
    rec = get_recommender()
    rec.reload()
    member_id = int(member["id"]) if member else None
    products, total, strategy = rec.for_you_page(db, member_id, pageNum, pageSize)
    data = page_result(products, total, pageNum, pageSize)
    data["strategy"] = strategy
    data["modelReady"] = rec.ready
    return success(data)


@router.get("/guessYouLike")
def guess_you_like(
    pageSize: int = Query(10, ge=1, le=30),
    productId: int | None = Query(None, description="Anchor product for anonymous users"),
    member: dict | None = Depends(get_optional_member),
    db: Session = Depends(get_db),
):
    """Personalized guess-you-like list (ItemCF). Falls back to hot items."""
    rec = get_recommender()
    rec.reload()
    member_id = int(member["id"]) if member else None
    ids, strategy = rec.guess_for_member(db, member_id, pageSize, productId)
    products = rec.fetch_products_by_ids(db, ids)
    return success(
        {
            "list": products,
            "strategy": strategy,
            "modelReady": rec.ready,
            "metrics": rec.manifest.get("metrics"),
        }
    )


@router.get("/similar/{product_id}")
def similar_products(
    product_id: int,
    pageSize: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Item-based similar products for product detail page."""
    rec = get_recommender()
    rec.reload()
    ids = rec.similar_products(product_id, pageSize)
    products = rec.fetch_products_by_ids(db, ids)
    return success({"list": products, "modelReady": rec.ready})
