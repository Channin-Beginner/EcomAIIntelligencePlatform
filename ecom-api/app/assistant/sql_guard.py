from __future__ import annotations

import json
import re
from pathlib import Path

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|GRANT|REVOKE|"
    r"INTO\s+OUTFILE|LOAD\s+DATA|FOR\s+UPDATE|CALL|EXECUTE|MERGE)\b",
    re.IGNORECASE,
)
MULTI_STMT = re.compile(r";")
COMMENT = re.compile(r"(--|/\*)")
TABLE_REF = re.compile(r"\b(?:FROM|JOIN)\s+`?([a-zA-Z0-9_]+)`?", re.IGNORECASE)
LIMIT_CLAUSE = re.compile(r"\bLIMIT\s+(\d+)", re.IGNORECASE)

MAX_LIMIT = 500
_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "docs" / "mall_schema_for_llm.json"


def _load_whitelist() -> set[str]:
    if not _SCHEMA_PATH.exists():
        return {
            "ads_order_daily",
            "ads_order_hourly",
            "ads_funnel_daily",
            "ads_member_active",
            "ads_region_sales",
            "ads_product_top",
            "ads_order_status",
            "ecom_event_log",
            "oms_order",
            "oms_order_item",
            "pms_product",
            "pms_brand",
        }
    data = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return set(data.get("allowed_tables", {}).keys())


def validate_sql(sql: str) -> tuple[str, list[str]]:
    """校验并规范化 SQL，返回 (safe_sql, errors)。"""
    errors: list[str] = []
    raw = sql.strip().rstrip(";")
    if not raw:
        return raw, ["SQL 为空"]

    upper = raw.upper()
    if not upper.startswith("SELECT"):
        errors.append("仅允许 SELECT 查询")

    if FORBIDDEN.search(raw):
        errors.append("包含禁止的关键字")

    if MULTI_STMT.search(raw):
        errors.append("禁止多语句")

    if COMMENT.search(raw):
        errors.append("禁止 SQL 注释")

    whitelist = _load_whitelist()
    tables = {t.lower() for t in TABLE_REF.findall(raw)}
    unknown = [t for t in tables if t.lower() not in whitelist]
    if unknown:
        errors.append(f"表不在白名单: {', '.join(unknown)}")

    safe = raw
    limit_match = LIMIT_CLAUSE.search(safe)
    if not limit_match:
        safe = f"{safe} LIMIT {MAX_LIMIT}"
    else:
        val = int(limit_match.group(1))
        if val > MAX_LIMIT:
            safe = LIMIT_CLAUSE.sub(f"LIMIT {MAX_LIMIT}", safe, count=1)

    return safe, errors
