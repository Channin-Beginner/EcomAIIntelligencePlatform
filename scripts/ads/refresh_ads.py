#!/usr/bin/env python3
"""Refresh ADS tables from OLTP + ecom_event_log. Run after seed import."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "ecom-api"
sys.path.insert(0, str(API_DIR))
os.chdir(API_DIR)

from app.admin.ads_refresh import refresh_ads_tables


def main() -> None:
    print("Refreshing ADS tables...")
    counts = refresh_ads_tables()
    for table, cnt in counts.items():
        print(f"  {table}: {cnt} rows")
    print("Done.")


if __name__ == "__main__":
    main()
