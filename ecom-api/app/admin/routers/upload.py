import uuid

from fastapi import APIRouter, Depends

from app.common.auth import get_current_admin
from app.common.response import success

router = APIRouter(prefix="/aliyun/oss", tags=["admin-upload"])


@router.get("/policy")
def oss_policy(_: dict = Depends(get_current_admin)):
    """Return a stub OSS upload policy for local development."""
    return success(
        {
            "accessKeyId": "local-dev",
            "policy": "local-dev-policy",
            "signature": "local-dev-signature",
            "dir": "mall/images/",
            "host": "https://local-dev.example.com",
            "callback": None,
            "key": f"mall/images/{uuid.uuid4().hex}.jpg",
        }
    )
