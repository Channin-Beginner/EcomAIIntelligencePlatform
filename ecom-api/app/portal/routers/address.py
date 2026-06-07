from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.common.auth import get_current_member
from app.common.response import success
from app.database import execute, fetch_all, fetch_one, get_db

router = APIRouter(prefix="/member/address", tags=["portal-address"])


class AddressBody(BaseModel):
    name: str
    phoneNumber: str
    defaultStatus: int = 0
    postCode: str | None = None
    province: str
    city: str
    region: str
    detailAddress: str


@router.get("/list")
def address_list(db: Session = Depends(get_db), member: dict = Depends(get_current_member)):
    rows = fetch_all(
        db,
        "SELECT * FROM ums_member_receive_address WHERE member_id = :mid",
        {"mid": member["id"]},
    )
    return success(rows)


@router.post("/add")
def address_add(body: AddressBody, db: Session = Depends(get_db), member: dict = Depends(get_current_member)):
    if body.defaultStatus == 1:
        execute(
            db,
            "UPDATE ums_member_receive_address SET default_status = 0 WHERE member_id = :mid",
            {"mid": member["id"]},
        )
    execute(
        db,
        """
        INSERT INTO ums_member_receive_address (
            member_id, name, phone_number, default_status, post_code,
            province, city, region, detail_address
        ) VALUES (
            :mid, :name, :phone, :def, :post,
            :prov, :city, :region, :detail
        )
        """,
        {
            "mid": member["id"],
            "name": body.name,
            "phone": body.phoneNumber,
            "def": body.defaultStatus,
            "post": body.postCode,
            "prov": body.province,
            "city": body.city,
            "region": body.region,
            "detail": body.detailAddress,
        },
    )
    db.commit()
    return success(1)


@router.get("/{address_id}")
def address_detail(address_id: int, db: Session = Depends(get_db), member: dict = Depends(get_current_member)):
    row = fetch_one(
        db,
        "SELECT * FROM ums_member_receive_address WHERE id = :id AND member_id = :mid",
        {"id": address_id, "mid": member["id"]},
    )
    return success(row)
