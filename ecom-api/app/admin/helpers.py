"""Shared helpers for admin API routers."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.common.response import page_result
from app.database import fetch_all, fetch_one


def snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def keys_to_camel(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {snake_to_camel(k): keys_to_camel(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [keys_to_camel(i) for i in obj]
    return obj


def keys_to_snake(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {camel_to_snake(k): keys_to_snake(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [keys_to_snake(i) for i in obj]
    return obj


def parse_ids(ids: str | None) -> list[int]:
    if not ids:
        return []
    return [int(x.strip()) for x in str(ids).split(",") if x.strip()]


def in_ids_sql(id_list: list[int]) -> str:
    if not id_list:
        return "0"
    return ",".join(str(int(i)) for i in id_list)


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return str(value)
    return value


def serialize_row(row: dict | None, extra_decimal: tuple[str, ...] = ()) -> dict | None:
    if row is None:
        return None
    out: dict[str, Any] = {}
    for key, value in row.items():
        if value is None:
            out[key] = None
        elif isinstance(value, Decimal) or key in extra_decimal:
            out[key] = float(value) if value is not None else None
        elif isinstance(value, (datetime, date)):
            out[key] = str(value)
        else:
            out[key] = value
    return keys_to_camel(out)


def serialize_rows(rows: list[dict], extra_decimal: tuple[str, ...] = ()) -> list[dict]:
    return [serialize_row(r, extra_decimal) or {} for r in rows]


def paginate(
    db: Session,
    table: str,
    where: str,
    params: dict,
    page_num: int,
    page_size: int,
    order_by: str = "id DESC",
    columns: str = "*",
    extra_decimal: tuple[str, ...] = (),
) -> dict:
    total_row = fetch_one(db, f"SELECT COUNT(*) AS cnt FROM {table} WHERE {where}", params)
    total = int(total_row["cnt"]) if total_row else 0
    offset = (page_num - 1) * page_size
    q = {**params, "limit": page_size, "offset": offset}
    rows = fetch_all(
        db,
        f"SELECT {columns} FROM {table} WHERE {where} ORDER BY {order_by} LIMIT :limit OFFSET :offset",
        q,
    )
    return page_result(serialize_rows(rows, extra_decimal), total, page_num, page_size)


def insert_from_body(db: Session, table: str, body: dict, exclude: set[str] | None = None) -> int:
    exclude = exclude or {"id"}
    data = keys_to_snake(body)
    for key in list(data.keys()):
        if key in exclude:
            data.pop(key, None)
    if not data:
        return 0
    cols = ", ".join(data.keys())
    vals = ", ".join(f":{k}" for k in data.keys())
    db.execute(
        __import__("sqlalchemy").text(f"INSERT INTO {table} ({cols}) VALUES ({vals})"),
        data,
    )
    row = fetch_one(db, "SELECT LAST_INSERT_ID() AS id")
    return int(row["id"]) if row else 0


def update_from_body(db: Session, table: str, row_id: int, body: dict, exclude: set[str] | None = None) -> int:
    exclude = (exclude or {"id"}) | {"id"}
    data = keys_to_snake(body)
    data = {k: v for k, v in data.items() if k not in exclude}
    if not data:
        return 0
    sets = ", ".join(f"{k} = :{k}" for k in data.keys())
    data["id"] = row_id
    result = db.execute(
        __import__("sqlalchemy").text(f"UPDATE {table} SET {sets} WHERE id = :id"),
        data,
    )
    return result.rowcount


def get_by_id(db: Session, table: str, row_id: int, extra_decimal: tuple[str, ...] = ()) -> dict | None:
    row = fetch_one(db, f"SELECT * FROM {table} WHERE id = :id", {"id": row_id})
    return serialize_row(row, extra_decimal)


def delete_by_id(db: Session, table: str, row_id: int) -> int:
    result = db.execute(
        __import__("sqlalchemy").text(f"DELETE FROM {table} WHERE id = :id"),
        {"id": row_id},
    )
    return result.rowcount


def update_status_by_ids(
    db: Session, table: str, ids: list[int], column: str, status: int
) -> int:
    if not ids:
        return 0
    result = db.execute(
        __import__("sqlalchemy").text(
            f"UPDATE {table} SET {column} = :status WHERE id IN ({in_ids_sql(ids)})"
        ),
        {"status": status},
    )
    return result.rowcount
