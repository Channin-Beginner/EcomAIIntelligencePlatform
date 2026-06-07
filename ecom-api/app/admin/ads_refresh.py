from __future__ import annotations

from sqlalchemy import text

from app.database import db_session, get_engine

ORDER_STATUS_NAMES = {
    0: "待付款",
    1: "待发货",
    2: "已发货",
    3: "已完成",
    4: "已关闭",
    5: "无效订单",
}

ADS_TABLES = [
    "ads_order_daily",
    "ads_order_hourly",
    "ads_funnel_daily",
    "ads_member_active",
    "ads_region_sales",
    "ads_product_top",
    "ads_order_status",
]


def _truncate_ads(conn) -> None:
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    for table in ADS_TABLES:
        conn.execute(text(f"TRUNCATE TABLE `{table}`"))
    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def refresh_ads_tables() -> dict:
    get_engine()
    with db_session() as db:
        conn = db.connection()
        _truncate_ads(conn)

        conn.execute(
            text(
                """
                INSERT INTO ads_order_daily (stat_date, order_count, gmv, paid_order_count, new_member_count)
                SELECT
                    DATE(o.create_time) AS stat_date,
                    COUNT(*) AS order_count,
                    COALESCE(SUM(o.pay_amount), 0) AS gmv,
                    SUM(CASE WHEN o.status >= 1 THEN 1 ELSE 0 END) AS paid_order_count,
                    0 AS new_member_count
                FROM oms_order o
                WHERE o.delete_status = 0
                GROUP BY DATE(o.create_time)
                """
            )
        )

        conn.execute(
            text(
                """
                UPDATE ads_order_daily d
                JOIN (
                    SELECT DATE(create_time) AS stat_date, COUNT(*) AS cnt
                    FROM ums_member
                    WHERE create_time IS NOT NULL
                    GROUP BY DATE(create_time)
                ) m ON d.stat_date = m.stat_date
                SET d.new_member_count = m.cnt
                """
            )
        )

        conn.execute(
            text(
                """
                INSERT INTO ads_order_hourly (stat_date, stat_hour, order_count, gmv)
                SELECT
                    DATE(o.create_time) AS stat_date,
                    HOUR(o.create_time) AS stat_hour,
                    COUNT(*) AS order_count,
                    COALESCE(SUM(o.pay_amount), 0) AS gmv
                FROM oms_order o
                WHERE o.delete_status = 0
                GROUP BY DATE(o.create_time), HOUR(o.create_time)
                """
            )
        )

        conn.execute(
            text(
                """
                INSERT INTO ads_funnel_daily (stat_date, pv_count, click_count, cart_count, fav_count, order_event_count)
                SELECT
                    DATE(e.event_time) AS stat_date,
                    SUM(CASE WHEN e.event_type = 'pv' THEN 1 ELSE 0 END) AS pv_count,
                    SUM(CASE WHEN e.event_type = 'click' THEN 1 ELSE 0 END) AS click_count,
                    SUM(CASE WHEN e.event_type = 'cart' THEN 1 ELSE 0 END) AS cart_count,
                    SUM(CASE WHEN e.event_type = 'fav' THEN 1 ELSE 0 END) AS fav_count,
                    SUM(CASE WHEN e.event_type = 'order' THEN 1 ELSE 0 END) AS order_event_count
                FROM ecom_event_log e
                GROUP BY DATE(e.event_time)
                """
            )
        )

        conn.execute(
            text(
                """
                INSERT INTO ads_member_active (stat_date, uv, pv, active_member_count)
                SELECT
                    DATE(e.event_time) AS stat_date,
                    COUNT(DISTINCT COALESCE(CAST(e.member_id AS CHAR), e.session_id)) AS uv,
                    SUM(CASE WHEN e.event_type = 'pv' THEN 1 ELSE 0 END) AS pv,
                    COUNT(DISTINCT CASE WHEN e.member_id IS NOT NULL THEN e.member_id END) AS active_member_count
                FROM ecom_event_log e
                GROUP BY DATE(e.event_time)
                """
            )
        )

        conn.execute(
            text(
                """
                INSERT INTO ads_region_sales (stat_date, province, order_count, gmv)
                SELECT
                    DATE(o.create_time) AS stat_date,
                    COALESCE(NULLIF(o.receiver_province, ''), '未知') AS province,
                    COUNT(*) AS order_count,
                    COALESCE(SUM(o.pay_amount), 0) AS gmv
                FROM oms_order o
                WHERE o.delete_status = 0
                GROUP BY DATE(o.create_time), COALESCE(NULLIF(o.receiver_province, ''), '未知')
                """
            )
        )

        conn.execute(
            text(
                """
                INSERT INTO ads_product_top (stat_date, rank_num, product_id, product_name, order_count, gmv)
                SELECT stat_date, rank_num, product_id, product_name, order_count, gmv
                FROM (
                    SELECT
                        DATE(o.create_time) AS stat_date,
                        oi.product_id,
                        MAX(oi.product_name) AS product_name,
                        COUNT(DISTINCT o.id) AS order_count,
                        COALESCE(SUM(COALESCE(oi.real_amount, oi.product_price * oi.product_quantity)), 0) AS gmv,
                        ROW_NUMBER() OVER (
                            PARTITION BY DATE(o.create_time)
                            ORDER BY SUM(COALESCE(oi.real_amount, oi.product_price * oi.product_quantity)) DESC
                        ) AS rank_num
                    FROM oms_order o
                    JOIN oms_order_item oi ON oi.order_id = o.id
                    WHERE o.delete_status = 0
                    GROUP BY DATE(o.create_time), oi.product_id
                ) ranked
                WHERE rank_num <= 10
                """
            )
        )

        for status, name in ORDER_STATUS_NAMES.items():
            conn.execute(
                text(
                    """
                    INSERT INTO ads_order_status (stat_date, status, status_name, order_count)
                    SELECT DATE(o.create_time), :status, :status_name, COUNT(*)
                    FROM oms_order o
                    WHERE o.delete_status = 0
                      AND o.status = :status
                    GROUP BY DATE(o.create_time)
                    """
                ),
                {"status": status, "status_name": name},
            )

        counts = {}
        for table in ADS_TABLES:
            row = conn.execute(text(f"SELECT COUNT(*) AS cnt FROM `{table}`")).mappings().first()
            counts[table] = int(row["cnt"]) if row else 0

        db.commit()
        return counts
