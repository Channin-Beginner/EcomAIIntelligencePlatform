from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.common.cors import add_cors
from app.portal.routers import address, brand, cart, collection, event, home, order, product, recommend, sso


@asynccontextmanager
async def portal_lifespan(_: FastAPI):
    from app.portal.schema import ensure_portal_tables

    ensure_portal_tables()
    yield


portal_app = FastAPI(title="EcomAI Portal API", version="0.1.0", lifespan=portal_lifespan)
add_cors(portal_app)

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


@portal_app.exception_handler(Exception)
async def portal_exception_handler(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"code": 500, "message": str(exc), "data": None})
