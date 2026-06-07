from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.common.auth import get_optional_member
from app.common.response import success, validate_failed
from app.database import get_db
from app.portal.event_log import ALLOWED_CLIENT_EVENTS, log_event

router = APIRouter(prefix="/event", tags=["portal-event"])


class TrackBody(BaseModel):
    eventType: str = Field(..., description="Implicit events only: pv | click")
    productId: int | None = None
    sessionId: str | None = None
    pagePath: str | None = None


@router.post("/track")
def track_event(
    body: TrackBody,
    db: Session = Depends(get_db),
    member: dict | None = Depends(get_optional_member),
):
    event_type = body.eventType.strip().lower()
    if event_type not in ALLOWED_CLIENT_EVENTS:
        return validate_failed("仅支持隐式行为埋点 pv / click")

    log_event(
        db,
        event_type,
        member_id=member["id"] if member else None,
        product_id=body.productId,
        session_id=body.sessionId,
        page_path=body.pagePath,
    )
    db.commit()
    return success(1)
