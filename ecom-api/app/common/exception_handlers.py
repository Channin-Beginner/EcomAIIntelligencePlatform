from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.logging_config import request_id_ctx
from app.config import get_settings

logger = logging.getLogger("ecom.error")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", request_id_ctx.get())


def _error_message(exc: Exception) -> str:
    settings = get_settings()
    if settings.app_env.lower() in {"dev", "development", "local"}:
        return str(exc)
    return "服务器内部错误，请稍后重试"


# def register_exception_handlers(app: FastAPI) -> None:
#     @app.exception_handler(StarletteHTTPException)
#     async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
#         request_id = _request_id(request)
#         detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
#         if exc.status_code >= 500:
#             logger.error(
#                 "HTTP %s path=%s request_id=%s detail=%s",
#                 exc.status_code,
#                 request.url.path,
#                 request_id,
#                 detail,
#             )
#         else:
#             logger.warning(
#                 "HTTP %s path=%s request_id=%s detail=%s",
#                 exc.status_code,
#                 request.url.path,
#                 request_id,
#                 detail,
#             )
#         return JSONResponse(
#             status_code=exc.status_code,
#             content={"code": exc.status_code, "message": detail, "data": None},
#         )

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = _request_id(request)
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        if exc.status_code >= 500:
            logger.error(
                "HTTP %s path=%s request_id=%s detail=%s",
                exc.status_code,
                request.url.path,
                request_id,
                detail,
            )
        else:
            logger.warning(
                "HTTP %s path=%s request_id=%s detail=%s",
                exc.status_code,
                request.url.path,
                request_id,
                detail,
            )
        response = JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": detail, "data": None},
        )
        # 关键修复：将响应对象保存到request.state，让PrometheusMiddleware能捕获到状态码
        request.state.response = response
        return response
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = _request_id(request)
        logger.warning(
            "Validation error path=%s request_id=%s errors=%s",
            request.url.path,
            request_id,
            exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content={"code": 422, "message": "参数检验失败", "data": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _request_id(request)
        logger.exception(
            "Unhandled exception path=%s request_id=%s",
            request.url.path,
            request_id,
        )
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": _error_message(exc), "data": None},
        )
