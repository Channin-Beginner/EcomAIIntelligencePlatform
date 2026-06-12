from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from sqlalchemy import text

from app.common.chaos_state import portal_500_active
from app.common.cors import add_cors
from app.common.exception_handlers import register_exception_handlers
from app.common.logging_config import setup_logging
from app.common.metrics import setup_metrics
from app.common.telemetry import setup_telemetry
from app.common.request_logging import add_request_logging
from app.config import get_settings
from app.database import get_engine
from app.portal.routers import address, brand, cart, collection, event, home, order, product, recommend, sso

logger = setup_logging("portal")


@asynccontextmanager
async def portal_lifespan(_: FastAPI):
    from app.portal.schema import ensure_portal_tables

    settings = get_settings()
    logger.info("Portal API starting env=%s port=%s", settings.app_env, settings.portal_port)
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception:
        logger.exception("Database connection check failed on startup")

    try:
        ensure_portal_tables()
        logger.info("Portal DDL bootstrap completed")
    except Exception:
        logger.exception("Portal DDL bootstrap failed")
        raise

    yield
    logger.info("Portal API shutting down")


portal_app = FastAPI(title="EcomAI Portal API", version="0.1.0", lifespan=portal_lifespan)
setup_telemetry(portal_app, "ecom-api-portal")
add_cors(portal_app)
add_request_logging(portal_app)
setup_metrics(portal_app)
register_exception_handlers(portal_app)

portal_app.include_router(sso.router)
portal_app.include_router(event.router)
portal_app.include_router(collection.router)
portal_app.include_router(home.router)
portal_app.include_router(product.router)
portal_app.include_router(brand.router)
portal_app.include_router(cart.router)
portal_app.include_router(address.router)
portal_app.include_router(order.router)
portal_app.include_router(recommend.router)


@portal_app.get("/health")
def health():
    return {"status": "ok", "service": "portal"}


@portal_app.get("/chaos/error")
def chaos_error():
    if portal_500_active():
        raise HTTPException(status_code=500, detail="chaos: portal 500 enabled")
    return {"status": "ok", "chaos": "portal-500 disabled"}
