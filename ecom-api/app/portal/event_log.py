from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.database import execute

ALLOWED_CLIENT_EVENTS = frozenset({"pv", "click"})


def log_event(
    db: Session,
    event_type: str,
    *,
    member_id: int | None = None,
    product_id: int | None = None,
    session_id: str | None = None,
    page_path: str | None = None,
    source: str = "web",
    event_time: datetime | None = None,
) -> None:
    execute(
        db,
        """
        INSERT INTO ecom_event_log (
            member_id, product_id, event_type, event_time, session_id, source, page_path
        ) VALUES (
            :member_id, :product_id, :event_type, :event_time, :session_id, :source, :page_path
        )
        """,
        {
            "member_id": member_id,
            "product_id": product_id,
            "event_type": event_type,
            "event_time": event_time or datetime.now(),
            "session_id": session_id,
            "source": source,
            "page_path": page_path,
        },
    )
