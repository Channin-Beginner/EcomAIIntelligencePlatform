from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.admin.routers import (
    admin_user,
    assistant,
    brand,
    chaos,
    cms,
    home,
    member_level,
    ops_stats,
    order,
    order_misc,
    product,
    product_attr,
    product_category,
    sku,
    sms,
    ums,
    upload,
)
from app.admin.routers.product_attr import attr_router, cate_router
from app.admin.routers.sms import coupon_router, flash_product_router, flash_router, flash_session_router
from app.admin.routers.ums import menu_router, resource_category_router, resource_router, role_router
from app.common.cors import add_cors
from app.common.exception_handlers import register_exception_handlers
from app.common.logging_config import setup_logging
from app.common.metrics import setup_metrics
from app.common.telemetry import setup_telemetry
from app.common.request_logging import add_request_logging
from app.config import get_settings
from app.database import get_engine

logger = setup_logging("admin")


@asynccontextmanager
async def admin_lifespan(_: FastAPI):
    settings = get_settings()
    logger.info("Admin API starting env=%s port=%s", settings.app_env, settings.admin_port)
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception:
        logger.exception("Database connection check failed on startup")
    yield
    logger.info("Admin API shutting down")


admin_app = FastAPI(title="EcomAI Admin API", version="0.1.0", lifespan=admin_lifespan)
setup_telemetry(admin_app, "ecom-api-admin")
add_cors(admin_app)
add_request_logging(admin_app)
setup_metrics(admin_app)
register_exception_handlers(admin_app)

admin_app.include_router(admin_user.router)
admin_app.include_router(product.router)
admin_app.include_router(order.router)
admin_app.include_router(brand.router)
admin_app.include_router(product_category.router)
admin_app.include_router(cms.router)
admin_app.include_router(member_level.router)
admin_app.include_router(order_misc.router)
admin_app.include_router(role_router)
admin_app.include_router(menu_router)
admin_app.include_router(resource_router)
admin_app.include_router(resource_category_router)
admin_app.include_router(attr_router)
admin_app.include_router(cate_router)
admin_app.include_router(sku.router)
admin_app.include_router(home.router)
admin_app.include_router(coupon_router)
admin_app.include_router(flash_router)
admin_app.include_router(flash_session_router)
admin_app.include_router(flash_product_router)
admin_app.include_router(upload.router)
admin_app.include_router(ops_stats.router)
admin_app.include_router(assistant.router)
admin_app.include_router(chaos.router)


@admin_app.get("/health")
def health():
    return {"status": "ok", "service": "admin"}
