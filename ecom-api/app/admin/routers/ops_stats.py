from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin import ops_service
from app.common.response import success
from app.database import get_db

router = APIRouter(prefix="/ops", tags=["ops-stats"])


@router.get("/dashboard/overview")
def dashboard_overview(
    refDate: str | None = Query(None, description="参考日期 YYYY-MM-DD，默认取 ADS 最新日"),
    db: Session = Depends(get_db),
):
    return success(ops_service.get_overview(db, refDate))


@router.get("/dashboard/order-hourly")
def dashboard_order_hourly(refDate: str | None = None, db: Session = Depends(get_db)):
    return success(ops_service.get_order_hourly(db, refDate))


@router.get("/dashboard/funnel")
def dashboard_funnel(refDate: str | None = None, db: Session = Depends(get_db)):
    return success(ops_service.get_funnel(db, refDate))


@router.get("/dashboard/member-active")
def dashboard_member_active(
    refDate: str | None = None,
    days: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_db),
):
    return success(ops_service.get_member_active(db, refDate, days))


@router.get("/dashboard/region-sales")
def dashboard_region_sales(
    refDate: str | None = None,
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return success(ops_service.get_region_sales(db, refDate, limit))


@router.get("/dashboard/order-trend")
def dashboard_order_trend(
    refDate: str | None = None,
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
):
    return success(ops_service.get_order_trend(db, refDate, days))


@router.get("/dashboard/product-top")
def dashboard_product_top(
    refDate: str | None = None,
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return success(ops_service.get_product_top(db, refDate, limit))


@router.get("/dashboard/order-status")
def dashboard_order_status(refDate: str | None = None, db: Session = Depends(get_db)):
    return success(ops_service.get_order_status(db, refDate))


@router.get("/ads/meta")
def ads_meta(db: Session = Depends(get_db)):
    return success(ops_service.get_ads_meta(db))


@router.post("/ads/refresh")
def ads_refresh():
    from app.admin.ads_refresh import refresh_ads_tables

    counts = refresh_ads_tables()
    return success({"refreshed": counts}, message="ADS 刷新完成")
