from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import fetch_all

ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = ROOT / "models" / "itemcf"
EVENT_WEIGHTS = {
    "order": 8.0,
    "cart": 4.0,
    "fav": 3.0,
    "click": 1.5,
    "pv": 0.5,
}
# ~23 day half-life for behavior signals
DECAY_LAMBDA = 0.03


class ItemCFRecommender:
    def __init__(self) -> None:
        self._item_similar: dict[str, list[dict]] = {}
        self._popular: list[int] = []
        self._manifest: dict = {}
        self._loaded_at = 0.0
        self._mtime = 0.0
        self.reload()

    def reload(self) -> bool:
        manifest_path = MODEL_DIR / "manifest.json"
        similar_path = MODEL_DIR / "item_similar.json"
        popular_path = MODEL_DIR / "popular.json"
        if not similar_path.exists():
            return False
        mtime = max(p.stat().st_mtime for p in (manifest_path, similar_path, popular_path) if p.exists())
        if mtime <= self._mtime and self._item_similar:
            return True
        self._item_similar = json.loads(similar_path.read_text(encoding="utf-8"))
        self._popular = json.loads(popular_path.read_text(encoding="utf-8")) if popular_path.exists() else []
        self._manifest = (
            json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        )
        self._mtime = mtime
        self._loaded_at = time.time()
        return True

    @property
    def ready(self) -> bool:
        return bool(self._item_similar)

    @property
    def manifest(self) -> dict:
        return dict(self._manifest)

    def _score_from_profile(
        self,
        profile: list[tuple[int, float]],
        exclude: set[int],
        top_k: int,
    ) -> list[int]:
        scores: dict[int, float] = defaultdict(float)
        for product_id, weight in profile:
            neighbors = self._item_similar.get(str(product_id), [])
            for entry in neighbors:
                pid = int(entry["productId"])
                if pid in exclude:
                    continue
                scores[pid] += float(entry["score"]) * weight
        if not scores:
            return []
        ranked = sorted(scores.items(), key=lambda x: (-x[1], -x[0]))
        return [pid for pid, _ in ranked[:top_k]]

    def similar_products(self, product_id: int, top_k: int = 10, exclude: set[int] | None = None) -> list[int]:
        exclude = exclude or set()
        exclude.add(product_id)
        neighbors = self._item_similar.get(str(product_id), [])
        result = []
        for entry in neighbors:
            pid = int(entry["productId"])
            if pid in exclude:
                continue
            result.append(pid)
            if len(result) >= top_k:
                break
        if len(result) < top_k:
            for pid in self._popular:
                if pid not in exclude and pid not in result:
                    result.append(pid)
                if len(result) >= top_k:
                    break
        return result

    @staticmethod
    def _decay_weight(base: float, event_time: datetime | None, now: datetime) -> float:
        if event_time is None:
            return base
        if isinstance(event_time, str):
            try:
                event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
            except ValueError:
                return base
        days = max(0.0, (now - event_time).total_seconds() / 86400.0)
        return base * math.exp(-DECAY_LAMBDA * days)

    def _merge_signal(
        self,
        merged: dict[int, float],
        product_id: int,
        base_weight: float,
        event_time: datetime | None,
        now: datetime,
    ) -> None:
        w = self._decay_weight(base_weight, event_time, now)
        merged[product_id] = max(merged.get(product_id, 0.0), w)

    def load_member_profile(self, db: Session, member_id: int, limit: int = 80) -> list[tuple[int, float]]:
        now = datetime.now()
        merged: dict[int, float] = {}

        event_rows = fetch_all(
            db,
            """
            SELECT product_id, event_type, MAX(event_time) AS event_time
            FROM ecom_event_log
            WHERE member_id = :mid AND product_id IS NOT NULL
              AND event_type IN ('order', 'cart', 'fav', 'click', 'pv')
            GROUP BY product_id, event_type
            """,
            {"mid": member_id},
        )
        for row in event_rows:
            pid = int(row["product_id"])
            base = EVENT_WEIGHTS.get(str(row["event_type"]), 0.5)
            self._merge_signal(merged, pid, base, row.get("event_time"), now)

        cart_rows = fetch_all(
            db,
            """
            SELECT product_id, MAX(modify_date) AS event_time
            FROM oms_cart_item
            WHERE member_id = :mid AND delete_status = 0
            GROUP BY product_id
            """,
            {"mid": member_id},
        )
        for row in cart_rows:
            self._merge_signal(merged, int(row["product_id"]), EVENT_WEIGHTS["cart"], row.get("event_time"), now)

        fav_rows = fetch_all(
            db,
            """
            SELECT product_id, MAX(create_time) AS event_time
            FROM ums_member_product_collection
            WHERE member_id = :mid
            GROUP BY product_id
            """,
            {"mid": member_id},
        )
        for row in fav_rows:
            self._merge_signal(merged, int(row["product_id"]), EVENT_WEIGHTS["fav"], row.get("event_time"), now)

        order_rows = fetch_all(
            db,
            """
            SELECT oi.product_id, MAX(o.create_time) AS event_time
            FROM oms_order o
            INNER JOIN oms_order_item oi ON o.id = oi.order_id
            WHERE o.member_id = :mid AND o.delete_status = 0
            GROUP BY oi.product_id
            """,
            {"mid": member_id},
        )
        for row in order_rows:
            self._merge_signal(merged, int(row["product_id"]), EVENT_WEIGHTS["order"], row.get("event_time"), now)

        profile = sorted(merged.items(), key=lambda x: (-x[1], -x[0]))[:limit]
        return profile

    def _score_all_from_profile(
        self,
        profile: list[tuple[int, float]],
        exclude: set[int],
    ) -> dict[int, float]:
        scores: dict[int, float] = defaultdict(float)
        for product_id, weight in profile:
            neighbors = self._item_similar.get(str(product_id), [])
            for entry in neighbors:
                pid = int(entry["productId"])
                if pid in exclude:
                    continue
                scores[pid] += float(entry["score"]) * weight
        return dict(scores)

    def _published_ids_by_sale(self, db: Session, exclude: set[int] | None = None) -> list[int]:
        exclude = exclude or set()
        rows = fetch_all(
            db,
            """
            SELECT id FROM pms_product
            WHERE publish_status = 1 AND delete_status = 0
            ORDER BY sale DESC, sort DESC, id DESC
            """,
        )
        return [int(r["id"]) for r in rows if int(r["id"]) not in exclude]

    def build_for_you_ranking(
        self,
        db: Session,
        member_id: int | None,
    ) -> tuple[list[int], str]:
        """Full product id list for 为你推荐: higher preference score first."""
        if not self.ready:
            ids = self._published_ids_by_sale(db)
            if not ids and self._popular:
                ids = list(self._popular)
            return ids, "popular_fallback"

        if member_id:
            profile = self.load_member_profile(db, member_id)
            if profile:
                exclude = {p for p, _ in profile}
                scores = self._score_all_from_profile(profile, exclude)
                ranked = sorted(scores.items(), key=lambda x: (-x[1], -x[0]))
                ranked_ids = [pid for pid, _ in ranked]
                seen = set(ranked_ids) | exclude
                for pid in self._published_ids_by_sale(db, exclude=seen):
                    ranked_ids.append(pid)
                if ranked_ids:
                    return ranked_ids, "itemcf_personal"

        popular = [p for p in self._popular if p]
        seen = set(popular)
        rest = self._published_ids_by_sale(db, exclude=seen)
        return popular + rest, "popular_fallback"

    def for_you_page(
        self,
        db: Session,
        member_id: int | None,
        page_num: int,
        page_size: int,
    ) -> tuple[list[dict], int, str]:
        all_ids, strategy = self.build_for_you_ranking(db, member_id)
        total = len(all_ids)
        start = (page_num - 1) * page_size
        page_ids = all_ids[start : start + page_size]
        products = self.fetch_products_by_ids(db, page_ids)
        return products, total, strategy

    def guess_for_member(
        self,
        db: Session,
        member_id: int | None,
        top_k: int = 10,
        seed_product_id: int | None = None,
    ) -> tuple[list[int], str]:
        """Returns (product_ids, strategy)."""
        if not self.ready:
            return self._popular[:top_k], "popular_fallback"

        if member_id:
            profile = self.load_member_profile(db, member_id)
            if profile:
                exclude = {p for p, _ in profile}
                recs = self._score_from_profile(profile, exclude, top_k)
                if recs:
                    return recs, "itemcf_personal"

        if seed_product_id:
            recs = self.similar_products(seed_product_id, top_k)
            if recs:
                return recs, "itemcf_similar"

        return self._popular[:top_k], "popular_fallback"

    def fetch_products_by_ids(self, db: Session, ids: list[int]) -> list[dict]:
        if not ids:
            return []
        id_sql = ", ".join(str(int(i)) for i in ids)
        rows = fetch_all(
            db,
            f"""
            SELECT id, name, pic, price, sub_title, sale, stock, brand_name, product_category_name
            FROM pms_product
            WHERE id IN ({id_sql}) AND publish_status = 1 AND delete_status = 0
            """,
        )
        by_id = {int(r["id"]): r for r in rows}
        ordered = []
        for pid in ids:
            row = by_id.get(pid)
            if row:
                item = dict(row)
                if item.get("price") is not None:
                    item["price"] = float(item["price"])
                ordered.append(item)
        return ordered


@lru_cache
def get_recommender() -> ItemCFRecommender:
    return ItemCFRecommender()
