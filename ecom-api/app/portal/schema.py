"""Ensure Portal-specific DDL exists (idempotent on startup)."""

import logging
from pathlib import Path

from sqlalchemy import text

from app.database import get_engine

logger = logging.getLogger("ecom.portal.schema")

ROOT = Path(__file__).resolve().parents[3]
DDL_DIR = ROOT / "sql" / "ddl"

PORTAL_DDL_FILES = (
    "ecom_event_log.sql",
    "ums_member_product_collection.sql",
)


def ensure_portal_tables() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        for name in PORTAL_DDL_FILES:
            path = DDL_DIR / name
            if not path.exists():
                logger.warning("Portal DDL file missing, skipped: %s", path)
                continue
            logger.info("Applying portal DDL: %s", name)
            sql = path.read_text(encoding="utf-8")
            for stmt in _split_sql_statements(sql):
                conn.execute(text(stmt))


def _split_sql_statements(sql: str) -> list[str]:
    parts: list[str] = []
    for chunk in sql.split(";"):
        stmt = _strip_leading_sql_comments(chunk).strip()
        if stmt:
            parts.append(stmt)
    return parts


def _strip_leading_sql_comments(chunk: str) -> str:
    """Drop full-line `--` comments so CREATE statements after headers are not skipped."""
    lines = [line for line in chunk.splitlines() if not line.strip().startswith("--")]
    return "\n".join(lines)
