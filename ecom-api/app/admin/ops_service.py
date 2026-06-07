from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import fetch_all, fetch_one

ORDER_STATUS_NAMES = {
    0: "待付款",
    1: "待发货",
    2: "已发货",
    3: "已完成",
    4: "已关闭",
    5: "无效订单",
}


def parse_ref_date(db: Session, ref_date: str | None) -> date:
    if ref_date:
        return datetime.strptime(ref_date, "%Y-%m-%d").date()
    row = fetch_one(db, "SELECT MAX(stat_date) AS d FROM ads_order_daily")
    if row and row.get("d"):
        val = row["d"]
        return val if isinstance(val, date) else datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    row = fetch_one(
        db,
        """
        SELECT MAX(DATE(create_time)) AS d FROM oms_order
        WHERE delete_status = 0
        """,
    )
    if row and row.get("d"):
        val = row["d"]
        return val if isinstance(val, date) else datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    return date.today()


def _serialize_decimal(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, datetime):
        return obj.isoformat(sep=" ", timespec="seconds")
    return obj


def _serialize_row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {k: _serialize_decimal(v) for k, v in row.items()}


def _serialize_rows(rows: list[dict]) -> list[dict]:
    return [_serialize_row(r) or {} for r in rows]


def _sum_period(db: Session, start: date, end: date) -> dict:
    row = fetch_one(
        db,
        """
        SELECT
            COALESCE(SUM(order_count), 0) AS order_count,
            COALESCE(SUM(gmv), 0) AS gmv
        FROM ads_order_daily
        WHERE stat_date >= :start AND stat_date <= :end
        """,
        {"start": start, "end": end},
    )
    if row and int(row.get("order_count") or 0) > 0:
        return _serialize_row(row) or {"order_count": 0, "gmv": 0}

    row = fetch_one(
        db,
        """
        SELECT COUNT(*) AS order_count, COALESCE(SUM(pay_amount), 0) AS gmv
        FROM oms_order
        WHERE delete_status = 0
          AND DATE(create_time) >= :start AND DATE(create_time) <= :end
        """,
        {"start": start, "end": end},
    )
    return _serialize_row(row) or {"order_count": 0, "gmv": 0}


def get_overview(db: Session, ref_date: str | None) -> dict:
    ref = parse_ref_date(db, ref_date)
    week_start = ref - timedelta(days=ref.weekday())
    month_start = ref.replace(day=1)

    today = _sum_period(db, ref, ref)
    week = _sum_period(db, week_start, ref)
    month = _sum_period(db, month_start, ref)

    prev_day = ref - timedelta(days=1)
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start - timedelta(days=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    yesterday = _sum_period(db, prev_day, prev_day)
    prev_week = _sum_period(db, prev_week_start, prev_week_end)
    prev_month = _sum_period(db, prev_month_start, prev_month_end)

    def pct(cur: float, prev: float) -> float | None:
        if prev == 0:
            return None
        return round((cur - prev) / prev * 100, 2)

    return {
        "refDate": ref.isoformat(),
        "today": {
            **today,
            "gmvChangePct": pct(float(today.get("gmv", 0)), float(yesterday.get("gmv", 0))),
            "orderChangePct": pct(float(today.get("order_count", 0)), float(yesterday.get("order_count", 0))),
        },
        "week": {
            **week,
            "gmvChangePct": pct(float(week.get("gmv", 0)), float(prev_week.get("gmv", 0))),
            "orderChangePct": pct(float(week.get("order_count", 0)), float(prev_week.get("order_count", 0))),
        },
        "month": {
            **month,
            "gmvChangePct": pct(float(month.get("gmv", 0)), float(prev_month.get("gmv", 0))),
            "orderChangePct": pct(float(month.get("order_count", 0)), float(prev_month.get("order_count", 0))),
        },
    }


def get_order_hourly(db: Session, ref_date: str | None) -> list[dict]:
    ref = parse_ref_date(db, ref_date)
    rows = fetch_all(
        db,
        """
        SELECT stat_hour, order_count, gmv
        FROM ads_order_hourly
        WHERE stat_date = :ref
        ORDER BY stat_hour
        """,
        {"ref": ref},
    )
    if rows:
        return _serialize_rows(rows)

    rows = fetch_all(
        db,
        """
        SELECT HOUR(create_time) AS stat_hour, COUNT(*) AS order_count, COALESCE(SUM(pay_amount), 0) AS gmv
        FROM oms_order
        WHERE delete_status = 0 AND DATE(create_time) = :ref
        GROUP BY HOUR(create_time)
        ORDER BY stat_hour
        """,
        {"ref": ref},
    )
    return _serialize_rows(rows)


def get_funnel(db: Session, ref_date: str | None) -> dict:
    ref = parse_ref_date(db, ref_date)
    row = fetch_one(
        db,
        "SELECT * FROM ads_funnel_daily WHERE stat_date = :ref",
        {"ref": ref},
    )
    if not row:
        row = fetch_one(
            db,
            """
            SELECT
                SUM(CASE WHEN event_type = 'pv' THEN 1 ELSE 0 END) AS pv_count,
                SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END) AS click_count,
                SUM(CASE WHEN event_type = 'cart' THEN 1 ELSE 0 END) AS cart_count,
                SUM(CASE WHEN event_type = 'fav' THEN 1 ELSE 0 END) AS fav_count,
                SUM(CASE WHEN event_type = 'order' THEN 1 ELSE 0 END) AS order_event_count
            FROM ecom_event_log
            WHERE DATE(event_time) = :ref
            """,
            {"ref": ref},
        )
    data = _serialize_row(row) or {}
    stages = [
        {"name": "浏览 PV", "value": int(data.get("pv_count") or 0)},
        {"name": "点击", "value": int(data.get("click_count") or 0)},
        {"name": "加购", "value": int(data.get("cart_count") or 0)},
        {"name": "收藏", "value": int(data.get("fav_count") or 0)},
        {"name": "下单", "value": int(data.get("order_event_count") or 0)},
    ]
    return {"refDate": ref.isoformat(), "stages": stages}


def get_member_active(db: Session, ref_date: str | None, days: int = 14) -> dict:
    ref = parse_ref_date(db, ref_date)
    start = ref - timedelta(days=days - 1)
    rows = fetch_all(
        db,
        """
        SELECT stat_date, uv, pv, active_member_count
        FROM ads_member_active
        WHERE stat_date >= :start AND stat_date <= :ref
        ORDER BY stat_date
        """,
        {"start": start, "ref": ref},
    )
    if not rows:
        rows = fetch_all(
            db,
            """
            SELECT
                DATE(event_time) AS stat_date,
                COUNT(DISTINCT COALESCE(CAST(member_id AS CHAR), session_id)) AS uv,
                SUM(CASE WHEN event_type = 'pv' THEN 1 ELSE 0 END) AS pv,
                COUNT(DISTINCT CASE WHEN member_id IS NOT NULL THEN member_id END) AS active_member_count
            FROM ecom_event_log
            WHERE DATE(event_time) >= :start AND DATE(event_time) <= :ref
            GROUP BY DATE(event_time)
            ORDER BY stat_date
            """,
            {"start": start, "ref": ref},
        )
    serialized = _serialize_rows(rows)
    latest = serialized[-1] if serialized else {"uv": 0, "pv": 0, "active_member_count": 0}
    return {"refDate": ref.isoformat(), "trend": serialized, "latest": latest}


def get_region_sales(db: Session, ref_date: str | None, limit: int = 10) -> dict:
    ref = parse_ref_date(db, ref_date)
    rows = fetch_all(
        db,
        """
        SELECT province, order_count, gmv
        FROM ads_region_sales
        WHERE stat_date = :ref
        ORDER BY gmv DESC
        LIMIT :limit
        """,
        {"ref": ref, "limit": limit},
    )
    if not rows:
        rows = fetch_all(
            db,
            """
            SELECT
                COALESCE(NULLIF(receiver_province, ''), '未知') AS province,
                COUNT(*) AS order_count,
                COALESCE(SUM(pay_amount), 0) AS gmv
            FROM oms_order
            WHERE delete_status = 0 AND DATE(create_time) = :ref
            GROUP BY COALESCE(NULLIF(receiver_province, ''), '未知')
            ORDER BY gmv DESC
            LIMIT :limit
            """,
            {"ref": ref, "limit": limit},
        )
    return {"refDate": ref.isoformat(), "regions": _serialize_rows(rows)}


def get_order_trend(db: Session, ref_date: str | None, days: int = 30) -> dict:
    ref = parse_ref_date(db, ref_date)
    start = ref - timedelta(days=days - 1)
    rows = fetch_all(
        db,
        """
        SELECT stat_date, order_count, gmv
        FROM ads_order_daily
        WHERE stat_date >= :start AND stat_date <= :ref
        ORDER BY stat_date
        """,
        {"start": start, "ref": ref},
    )
    if not rows:
        rows = fetch_all(
            db,
            """
            SELECT DATE(create_time) AS stat_date, COUNT(*) AS order_count, COALESCE(SUM(pay_amount), 0) AS gmv
            FROM oms_order
            WHERE delete_status = 0
              AND DATE(create_time) >= :start AND DATE(create_time) <= :ref
            GROUP BY DATE(create_time)
            ORDER BY stat_date
            """,
            {"start": start, "ref": ref},
        )
    return {"refDate": ref.isoformat(), "trend": _serialize_rows(rows)}


def get_product_top(db: Session, ref_date: str | None, limit: int = 10) -> dict:
    ref = parse_ref_date(db, ref_date)
    rows = fetch_all(
        db,
        """
        SELECT rank_num, product_id, product_name, order_count, gmv
        FROM ads_product_top
        WHERE stat_date = :ref
        ORDER BY rank_num
        LIMIT :limit
        """,
        {"ref": ref, "limit": limit},
    )
    if not rows:
        rows = fetch_all(
            db,
            """
            SELECT product_id, MAX(product_name) AS product_name,
                   COUNT(DISTINCT o.id) AS order_count,
                   COALESCE(SUM(COALESCE(oi.real_amount, oi.product_price * oi.product_quantity)), 0) AS gmv
            FROM oms_order o
            JOIN oms_order_item oi ON oi.order_id = o.id
            WHERE o.delete_status = 0 AND DATE(o.create_time) = :ref
            GROUP BY oi.product_id
            ORDER BY gmv DESC
            LIMIT :limit
            """,
            {"ref": ref, "limit": limit},
        )
        for i, row in enumerate(rows, 1):
            row["rank_num"] = i
    return {"refDate": ref.isoformat(), "products": _serialize_rows(rows)}


def get_order_status(db: Session, ref_date: str | None) -> dict:
    ref = parse_ref_date(db, ref_date)
    rows = fetch_all(
        db,
        """
        SELECT status, status_name, order_count
        FROM ads_order_status
        WHERE stat_date = :ref
        ORDER BY order_count DESC
        """,
        {"ref": ref},
    )
    if not rows:
        rows = fetch_all(
            db,
            """
            SELECT status, COUNT(*) AS order_count
            FROM oms_order
            WHERE delete_status = 0 AND DATE(create_time) = :ref
            GROUP BY status
            ORDER BY order_count DESC
            """,
            {"ref": ref},
        )
        for row in rows:
            row["status_name"] = ORDER_STATUS_NAMES.get(int(row["status"]), f"状态{row['status']}")
    return {"refDate": ref.isoformat(), "statuses": _serialize_rows(rows)}


def get_ads_meta(db: Session) -> dict:
    tables = [
        "ads_order_daily",
        "ads_order_hourly",
        "ads_funnel_daily",
        "ads_member_active",
        "ads_region_sales",
        "ads_product_top",
        "ads_order_status",
    ]
    meta = {}
    for table in tables:
        row = fetch_one(db, f"SELECT COUNT(*) AS cnt, MAX(updated_at) AS updated_at FROM `{table}`")
        meta[table] = _serialize_row(row)
    max_date = fetch_one(db, "SELECT MIN(stat_date) AS min_date, MAX(stat_date) AS max_date FROM ads_order_daily")
    return {"tables": meta, "dateRange": _serialize_row(max_date)}
