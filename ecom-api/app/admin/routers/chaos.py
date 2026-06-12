"""Chaos endpoints consumed by OpsAI scripts/chaos/*.py."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.common.chaos_state import portal_500_active, set_portal_500
from app.common.response import success
from app.database import get_db

router = APIRouter(prefix="/admin/chaos", tags=["admin-chaos"])


class Portal500Body(BaseModel):
    enable: bool = True
    route: str | None = None
    duration_seconds: int = Field(default=180, ge=1, le=3600)


class MysqlSlowBody(BaseModel):
    duration_seconds: int = Field(default=120, ge=1, le=3600)
    sleep_seconds: int = Field(default=3, ge=1, le=30)
    workers: int = Field(default=2, ge=1, le=16)


class LlmTimeoutBody(BaseModel):
    enable: bool = True
    timeout_seconds: int = Field(default=1, ge=1, le=120)
    duration_seconds: int = Field(default=120, ge=1, le=3600)


class AdsRefreshFailBody(BaseModel):
    enable: bool = True
    duration_seconds: int = Field(default=300, ge=1, le=3600)


@router.post("/portal-500")
def chaos_portal_500(body: Portal500Body):
    set_portal_500(body.enable, body.duration_seconds)
    return success(
        {
            "enable": body.enable,
            "duration_seconds": body.duration_seconds,
            "portal_route": body.route or "/chaos/error",
            "hint": "OpsAI: hammer GET /chaos/error on Portal after enable",
        }
    )


@router.post("/mysql-slow")
def chaos_mysql_slow(body: MysqlSlowBody):
    return success(
        {
            "duration_seconds": body.duration_seconds,
            "sleep_seconds": body.sleep_seconds,
            "workers": body.workers,
            "hammer_url": f"/admin/chaos/slow-query?sleep={body.sleep_seconds}",
            "hint": "OpsAI inject_slow_mysql should concurrent GET hammer_url on Admin",
        }
    )


@router.get("/slow-query")
def chaos_slow_query(
    sleep: int = Query(3, ge=1, le=30),
    db: Session = Depends(get_db),
):
    db.execute(text("SELECT SLEEP(:seconds)"), {"seconds": sleep})
    return success({"slept_seconds": sleep, "service": "ecom-api-admin"})


@router.post("/llm-timeout")
def chaos_llm_timeout(body: LlmTimeoutBody):
    return success(
        {
            "enable": body.enable,
            "timeout_seconds": body.timeout_seconds,
            "duration_seconds": body.duration_seconds,
            "note": "Adjust LLM_TIMEOUT in ecom-api/.env and restart if needed",
        }
    )


@router.post("/ads-refresh-fail")
def chaos_ads_refresh_fail(body: AdsRefreshFailBody):
    return success(
        {
            "enable": body.enable,
            "duration_seconds": body.duration_seconds,
            "note": "Demo flag only; wire ADS_REFRESH_CHAOS in ads job for real failure",
        }
    )


@router.get("/status")
def chaos_status():
    return success({"portal_500_active": portal_500_active()})
