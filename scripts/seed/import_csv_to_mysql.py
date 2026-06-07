"""
Import Phase-2 seed CSV files into MySQL (灌注数据/*.csv).

Reads DB config from ecom-api/.env. Idempotent: removes prior seed rows in
known ID ranges before re-import.

Run:
  python scripts/seed/import_csv_to_mysql.py
  python scripts/seed/import_csv_to_mysql.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from pymysql.connections import Connection

ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = ROOT / "灌注数据"
ENV_PATH = ROOT / "ecom-api" / ".env"

BATCH_SIZE = 2000

# Seed ID boundaries (must match generate_csv_data.py / manifest.json)
MEMBER_ID_START = 10001
MEMBER_ID_END = 13000
PRODUCT_ID_START = 1000
ORDER_ID_START = 100001
ORDER_ID_END = 110000
CART_ID_START = 100001
SKU_ID_START = 1000  # new seed SKUs only (product_id >= 1000)


def load_settings() -> dict:
    load_dotenv(ENV_PATH)
    import os

    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "mall"),
        "charset": "utf8mb4",
    }


def connect() -> Connection:
    cfg = load_settings()
    return pymysql.connect(**cfg, autocommit=False)


def nullify(row: dict[str, str]) -> dict:
    out: dict = {}
    for k, v in row.items():
        if v == "":
            out[k] = None
        else:
            out[k] = v
    return out


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = [nullify(r) for r in reader]
    return headers, rows


def batched(rows: list[dict], size: int):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def insert_rows(cur, table: str, headers: list[str], rows: list[dict]) -> int:
    if not rows:
        return 0
    cols = ", ".join(f"`{h}`" for h in headers)
    placeholders = ", ".join(["%s"] * len(headers))
    sql = f"INSERT INTO `{table}` ({cols}) VALUES ({placeholders})"
    total = 0
    for chunk in batched(rows, BATCH_SIZE):
        values = [tuple(r.get(h) for h in headers) for r in chunk]
        cur.executemany(sql, values)
        total += len(chunk)
    return total


def cleanup_seed(cur) -> None:
    """Remove previously imported seed data (reverse dependency order)."""
    statements = [
        "DELETE FROM ecom_event_log WHERE source = 'seed'",
        f"DELETE FROM oms_cart_item WHERE id >= {CART_ID_START}",
        "DELETE FROM pms_comment WHERE id BETWEEN 1 AND 5000",
        f"DELETE FROM oms_order_item WHERE id BETWEEN {ORDER_ID_START} AND {ORDER_ID_END}",
        f"DELETE FROM oms_order WHERE id BETWEEN {ORDER_ID_START} AND {ORDER_ID_END}",
        f"DELETE FROM pms_sku_stock WHERE product_id >= {PRODUCT_ID_START}",
        f"DELETE FROM pms_product WHERE id >= {PRODUCT_ID_START}",
        f"DELETE FROM ums_member_receive_address WHERE id BETWEEN {MEMBER_ID_START} AND {MEMBER_ID_END}",
        f"DELETE FROM ums_member WHERE id BETWEEN {MEMBER_ID_START} AND {MEMBER_ID_END}",
    ]
    for sql in statements:
        cur.execute(sql)


def apply_sale_updates(cur) -> None:
    path = CSV_DIR / "pms_product_sale_update.csv"
    if not path.exists():
        return
    _, rows = read_csv(path)
    for r in rows:
        cur.execute(
            "UPDATE pms_product SET sale = COALESCE(sale, 0) + %s WHERE id = %s",
            (int(r["sale_increment"]), int(r["product_id"])),
        )

    path = CSV_DIR / "pms_sku_stock_sale_update.csv"
    if not path.exists():
        return
    _, rows = read_csv(path)
    for r in rows:
        cur.execute(
            "UPDATE pms_sku_stock SET sale = COALESCE(sale, 0) + %s WHERE id = %s",
            (int(r["sale_increment"]), int(r["sku_id"])),
        )


def bump_auto_increment(cur) -> None:
    bumps = [
        ("ums_member", MEMBER_ID_END + 1),
        ("ums_member_receive_address", MEMBER_ID_END + 1),
        ("pms_product", 1320),
        ("pms_sku_stock", 2000),
        ("oms_order", ORDER_ID_END + 1),
        ("oms_order_item", ORDER_ID_END + 1),
        ("pms_comment", 5001),
        ("oms_cart_item", CART_ID_START + 15000),
        ("ecom_event_log", 200001),
    ]
    for table, next_id in bumps:
        cur.execute(f"ALTER TABLE `{table}` AUTO_INCREMENT = %s", (next_id,))


def verify_counts(cur) -> dict[str, int]:
    checks = {
        "ums_member_seed": f"SELECT COUNT(*) FROM ums_member WHERE id BETWEEN {MEMBER_ID_START} AND {MEMBER_ID_END}",
        "pms_product_seed": f"SELECT COUNT(*) FROM pms_product WHERE id >= {PRODUCT_ID_START}",
        "oms_order_seed": f"SELECT COUNT(*) FROM oms_order WHERE id BETWEEN {ORDER_ID_START} AND {ORDER_ID_END}",
        "ecom_event_log_seed": "SELECT COUNT(*) FROM ecom_event_log WHERE source = 'seed'",
        "pms_comment_seed": "SELECT COUNT(*) FROM pms_comment WHERE id BETWEEN 1 AND 5000",
        "oms_cart_item_seed": f"SELECT COUNT(*) FROM oms_cart_item WHERE id >= {CART_ID_START}",
    }
    out = {}
    for key, sql in checks.items():
        cur.execute(sql)
        out[key] = cur.fetchone()[0]
    return out


IMPORT_PLAN: list[tuple[str, str]] = [
    ("ums_member.csv", "ums_member"),
    ("ums_member_receive_address.csv", "ums_member_receive_address"),
    ("pms_product.csv", "pms_product"),
    ("pms_sku_stock.csv", "pms_sku_stock"),
    ("oms_order.csv", "oms_order"),
    ("oms_order_item.csv", "oms_order_item"),
    ("pms_comment.csv", "pms_comment"),
    ("oms_cart_item.csv", "oms_cart_item"),
    ("ecom_event_log.csv", "ecom_event_log"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Import 灌注数据 CSV files into MySQL")
    parser.add_argument("--dry-run", action="store_true", help="Validate files only, no DB writes")
    args = parser.parse_args()

    if not CSV_DIR.exists():
        print(f"CSV directory not found: {CSV_DIR}", file=sys.stderr)
        return 1

    missing = [name for name, _ in IMPORT_PLAN if not (CSV_DIR / name).exists()]
    if missing:
        print(f"Missing CSV files: {missing}", file=sys.stderr)
        return 1

    if args.dry_run:
        for fname, table in IMPORT_PLAN:
            headers, rows = read_csv(CSV_DIR / fname)
            print(f"[dry-run] {fname} -> {table}: {len(rows)} rows, {len(headers)} cols")
        print("[dry-run] OK")
        return 0

    conn = connect()
    try:
        with conn.cursor() as cur:
            print("Cleaning prior seed rows...")
            cleanup_seed(cur)

            totals: dict[str, int] = {}
            for fname, table in IMPORT_PLAN:
                headers, rows = read_csv(CSV_DIR / fname)
                print(f"Importing {fname} -> {table} ({len(rows)} rows)...")
                totals[table] = insert_rows(cur, table, headers, rows)

            print("Applying sale increments...")
            apply_sale_updates(cur)

            print("Updating AUTO_INCREMENT...")
            bump_auto_increment(cur)

            conn.commit()

            counts = verify_counts(cur)
            print("\n=== Import complete ===")
            for table, n in totals.items():
                print(f"  inserted {table}: {n:,}")
            print("\n=== Verification ===")
            for k, v in counts.items():
                print(f"  {k}: {v:,}")
    except Exception as exc:
        conn.rollback()
        print(f"Import failed, rolled back: {exc}", file=sys.stderr)
        raise
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
