from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.helpers import paginate
from app.common.auth import get_current_admin
from app.common.response import success
from app.database import get_db

router = APIRouter(prefix="/memberLevel", tags=["admin-member-level"])


@router.get("/list")
def member_level_list(
    defaultStatus: int | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if defaultStatus is not None:
        conditions.append("default_status = :defaultStatus")
        params["defaultStatus"] = defaultStatus
    return success(
        paginate(db, "ums_member_level", " AND ".join(conditions), params, pageNum, pageSize, "id ASC")
    )
