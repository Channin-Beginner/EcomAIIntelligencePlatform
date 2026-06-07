from __future__ import annotations

import re
from typing import Literal

from sqlalchemy.orm import Session

from app.admin import ops_service
from app.assistant import chart_builder

TemplateKind = Literal[
    "overview",
    "hourly",
    "funnel",
    "member",
    "regions",
    "trend",
    "products",
    "status",
    "none",
]

_RULES: list[tuple[TemplateKind, list[str]]] = [
    ("hourly", [r"24\s*小时", r"小时.*(曲线|销售|gmv)", r"分时", r"按小时"]),
    ("funnel", [r"漏斗", r"转化"]),
    ("member", [r"\buv\b", r"\bpv\b", r"活跃", r"访客"]),
    ("regions", [r"地域", r"省份", r"地区.*(销售|gmv|top)"]),
    ("trend", [r"趋势", r"近\s*\d+\s*天", r"30\s*日", r"走势"]),
    ("products", [r"热销", r"商品.*top", r"top\s*\d+.*商品", r"畅销"]),
    ("status", [r"订单状态", r"状态分布", r"待付款", r"待发货"]),
    ("overview", [r"gmv", r"订单数", r"核心", r"kpi", r"今日", r"当天", r"本周", r"本月", r"环比"]),
]


def match_template(question: str) -> TemplateKind:
    q = question.lower()
    best: TemplateKind = "none"
    best_score = 0
    for kind, patterns in _RULES:
        score = sum(1 for p in patterns if re.search(p, q, re.IGNORECASE))
        if score > best_score:
            best_score = score
            best = kind
    return best if best_score > 0 else "none"


def run_template(
    db: Session,
    kind: TemplateKind,
    ref_date: str | None,
) -> tuple[str, dict, dict | None, str] | None:
    if kind == "none":
        return None

    if kind == "overview":
        data = ops_service.get_overview(db, ref_date)
        answer, chart, table = chart_builder.from_template_overview(data)
        return answer, chart, table, "template:overview"

    if kind == "hourly":
        ref = ops_service.parse_ref_date(db, ref_date)
        data = ops_service.get_order_hourly(db, ref_date)
        answer, chart, table = chart_builder.from_template_hourly(data, ref.isoformat())
        return answer, chart, table, "template:hourly"

    if kind == "funnel":
        data = ops_service.get_funnel(db, ref_date)
        answer, chart, table = chart_builder.from_template_funnel(data)
        return answer, chart, table, "template:funnel"

    if kind == "member":
        data = ops_service.get_member_active(db, ref_date, 14)
        answer, chart, table = chart_builder.from_template_member(data)
        return answer, chart, table, "template:member"

    if kind == "regions":
        data = ops_service.get_region_sales(db, ref_date, 10)
        answer, chart, table = chart_builder.from_template_regions(data)
        return answer, chart, table, "template:regions"

    if kind == "trend":
        data = ops_service.get_order_trend(db, ref_date, 30)
        answer, chart, table = chart_builder.from_template_trend(data)
        return answer, chart, table, "template:trend"

    if kind == "products":
        data = ops_service.get_product_top(db, ref_date, 10)
        answer, chart, table = chart_builder.from_template_products(data)
        return answer, chart, table, "template:products"

    if kind == "status":
        data = ops_service.get_order_status(db, ref_date)
        answer, chart, table = chart_builder.from_template_status(data)
        return answer, chart, table, "template:status"

    return None
