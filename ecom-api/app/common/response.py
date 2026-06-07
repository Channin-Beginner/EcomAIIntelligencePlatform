from typing import Any

from fastapi.responses import JSONResponse


def success(data: Any = None, message: str = "操作成功") -> dict:
    return {"code": 200, "message": message, "data": data}


def failed(message: str = "操作失败", code: int = 500) -> dict:
    return {"code": code, "message": message, "data": None}


def validate_failed(message: str = "参数检验失败") -> dict:
    return {"code": 404, "message": message, "data": None}


def unauthorized() -> JSONResponse:
    return JSONResponse(status_code=200, content={"code": 401, "message": "暂未登录或token已经过期", "data": None})


def page_result(items: list, total: int, page_num: int, page_size: int) -> dict:
    total_page = (total + page_size - 1) // page_size if page_size else 0
    return {
        "pageNum": page_num,
        "pageSize": page_size,
        "totalPage": total_page,
        "total": total,
        "list": items,
    }
