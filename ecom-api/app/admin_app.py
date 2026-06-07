from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.admin.routers import (
    admin_user,
    brand,
    cms,
    home,
    member_level,
    assistant,
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

admin_app = FastAPI(title="EcomAI Admin API", version="0.1.0")
add_cors(admin_app)

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


@admin_app.get("/health")
def health():
    return {"status": "ok", "service": "admin"}


@admin_app.exception_handler(Exception)
async def admin_exception_handler(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"code": 500, "message": str(exc), "data": None})
