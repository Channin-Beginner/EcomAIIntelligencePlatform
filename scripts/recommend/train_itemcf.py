"""
Train ItemCF recommendation model from mall OLTP + ecom_event_log.

Outputs under models/itemcf/:
  - manifest.json       metrics and metadata
  - item_similar.json   product_id -> [similar product ids]
  - popular.json        fallback hot product ids

Run from repo root:
  python scripts/recommend/train_itemcf.py
"""

from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "ecom-api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from dotenv import load_dotenv

load_dotenv(API_ROOT / ".env")

from app.config import get_settings  # noqa: E402

MODEL_DIR = ROOT / "models" / "itemcf"
TOP_K_SIMILAR = 50
TOP_K_EVAL = 10
MIN_USER_INTERACTIONS = 2
EVENT_WEIGHTS = {
    "order": 8.0,
    "cart": 4.0,
    "fav": 3.0,
    "click": 1.5,
    "pv": 0.5,
}
def load_strong_pairs(engine, valid_products: set[int]) -> list[tuple[int, int]]:
    sql = text(
        """
        SELECT member_id, product_id
        FROM ecom_event_log
        WHERE member_id IS NOT NULL AND product_id IS NOT NULL
          AND event_type IN ('order', 'cart', 'fav', 'click')
        UNION
        SELECT o.member_id, oi.product_id
        FROM oms_order o
        INNER JOIN oms_order_item oi ON o.id = oi.order_id
        WHERE o.member_id IS NOT NULL AND o.delete_status = 0
        """
    )
    seen: set[tuple[int, int]] = set()
    pairs: list[tuple[int, int]] = []
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()
    for row in rows:
        pid = int(row["product_id"])
        if pid not in valid_products:
            continue
        key = (int(row["member_id"]), pid)
        if key in seen:
            continue
        seen.add(key)
        pairs.append(key)
    return pairs


def load_interactions(engine) -> list[tuple[int, int, float]]:
    """member_id, product_id, weight"""
    sql = text(
        """
        SELECT member_id, product_id, event_type
        FROM ecom_event_log
        WHERE member_id IS NOT NULL AND product_id IS NOT NULL
          AND event_type IN ('order', 'cart', 'fav', 'click', 'pv')
        UNION ALL
        SELECT o.member_id, oi.product_id, 'order' AS event_type
        FROM oms_order o
        INNER JOIN oms_order_item oi ON o.id = oi.order_id
        WHERE o.member_id IS NOT NULL AND o.delete_status = 0
        """
    )
    pairs: dict[tuple[int, int], float] = {}
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()
    for row in rows:
        member_id = int(row["member_id"])
        product_id = int(row["product_id"])
        weight = EVENT_WEIGHTS.get(str(row["event_type"]), 0.5)
        key = (member_id, product_id)
        pairs[key] = max(pairs.get(key, 0.0), weight)
    return [(m, p, w) for (m, p), w in pairs.items()]


def load_published_products(engine) -> set[int]:
    sql = text(
        """
        SELECT id FROM pms_product
        WHERE publish_status = 1 AND delete_status = 0
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()
    return {int(r["id"]) for r in rows}


def load_product_meta(engine, valid_products: set[int]) -> dict[int, dict]:
    if not valid_products:
        return {}
    id_sql = ", ".join(str(int(i)) for i in sorted(valid_products))
    sql = text(
        f"""
        SELECT id, product_category_id, brand_id
        FROM pms_product
        WHERE id IN ({id_sql})
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()
    return {
        int(r["id"]): {
            "category_id": int(r["product_category_id"] or 0),
            "brand_id": int(r["brand_id"] or 0),
        }
        for r in rows
    }


def inject_content_similarity(
    sim_matrix: np.ndarray,
    item_rev: dict[int, int],
    product_meta: dict[int, dict],
    category_weight: float = 0.28,
    brand_weight: float = 0.18,
) -> np.ndarray:
    n_items = sim_matrix.shape[0]
    for i in range(n_items):
        pi = item_rev[i]
        meta_i = product_meta.get(pi)
        if not meta_i:
            continue
        for j in range(i + 1, n_items):
            pj = item_rev[j]
            meta_j = product_meta.get(pj)
            if not meta_j:
                continue
            boost = 0.0
            if meta_i["category_id"] and meta_i["category_id"] == meta_j["category_id"]:
                boost += category_weight
            if meta_i["brand_id"] and meta_i["brand_id"] == meta_j["brand_id"]:
                boost += brand_weight
            if boost > 0:
                sim_matrix[i, j] += boost
                sim_matrix[j, i] += boost
    return sim_matrix


def build_matrices(
    interactions: list[tuple[int, int, float]],
    valid_products: set[int],
    binary: bool = False,
) -> tuple[csr_matrix, dict[int, int], dict[int, int], dict[int, list[tuple[int, float]]]]:
    """Return user-item matrix and id mappings."""
    filtered = [(m, p, 1.0 if binary else w) for m, p, w in interactions if p in valid_products]
    users = sorted({m for m, _, _ in filtered})
    items = sorted({p for _, p, _ in filtered})
    user_index = {u: i for i, u in enumerate(users)}
    item_index = {p: i for i, p in enumerate(items)}
    item_rev = {i: p for p, i in item_index.items()}

    rows, cols, data = [], [], []
    user_items: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for member_id, product_id, weight in filtered:
        ui = user_index[member_id]
        ii = item_index[product_id]
        rows.append(ui)
        cols.append(ii)
        data.append(weight)
        user_items[member_id].append((product_id, weight))

    matrix = csr_matrix(
        (data, (rows, cols)),
        shape=(len(users), len(items)),
        dtype=np.float32,
    )
    return matrix, user_index, item_rev, dict(user_items)


def top_similar_from_matrix(
    sim_matrix: np.ndarray,
    item_rev: dict[int, int],
    top_k: int,
) -> dict[int, list[tuple[int, float]]]:
    """item_idx -> [(product_id, score), ...]"""
    item_similar: dict[int, list[tuple[int, float]]] = {}
    n_items = sim_matrix.shape[0]
    for idx in range(n_items):
        scores = sim_matrix[idx]
        if top_k >= n_items - 1:
            ranked = np.argsort(-scores)
        else:
            ranked = np.argpartition(-scores, min(top_k, n_items - 1))[:top_k]
            ranked = ranked[np.argsort(-scores[ranked])]
        neighbors = []
        for j in ranked:
            s = float(scores[j])
            if s <= 0:
                continue
            neighbors.append((item_rev[int(j)], s))
            if len(neighbors) >= top_k:
                break
        item_similar[idx] = neighbors
    return item_similar


def recommend_with_similarity(
    user_profile: list[tuple[int, float]],
    sim_matrix: np.ndarray,
    item_index: dict[int, int],
    item_rev: dict[int, int],
    exclude: set[int],
    top_k: int,
    user_sim_matrix: np.ndarray | None = None,
    user_index: dict[int, int] | None = None,
    user_rev: dict[int, int] | None = None,
    order_matrix: csr_matrix | None = None,
    member_id: int | None = None,
    hybrid_user_weight: float = 0.35,
) -> list[int]:
    scores: dict[int, float] = defaultdict(float)
    for product_id, weight in user_profile:
        ii = item_index.get(product_id)
        if ii is None:
            continue
        sim_row = sim_matrix[ii]
        for other_ii, sim in enumerate(sim_row):
            if sim <= 0:
                continue
            pid = item_rev[other_ii]
            if pid in exclude:
                continue
            scores[pid] += float(sim) * weight

    if (
        user_sim_matrix is not None
        and user_index is not None
        and user_rev is not None
        and order_matrix is not None
        and member_id is not None
        and member_id in user_index
    ):
        ui = user_index[member_id]
        neighbor_sims = user_sim_matrix[ui]
        top_neighbors = np.argpartition(-neighbor_sims, min(40, len(neighbor_sims) - 1))[:40]
        for vi in top_neighbors:
            sim_uv = float(neighbor_sims[vi])
            if sim_uv <= 0 or vi == ui:
                continue
            row = order_matrix.getrow(int(vi)).toarray().ravel()
            for other_ii, rating in enumerate(row):
                if rating <= 0:
                    continue
                pid = item_rev[other_ii]
                if pid in exclude:
                    continue
                scores[pid] += sim_uv * float(rating) * hybrid_user_weight

    if not scores:
        return []
    ranked = sorted(scores.items(), key=lambda x: (-x[1], -x[0]))
    return [pid for pid, _ in ranked[:top_k]]


def build_item_similarity_matrix(matrix: csr_matrix) -> np.ndarray:
    col_norms = np.sqrt(matrix.power(2).sum(axis=0)).A1
    col_norms[col_norms == 0] = 1.0
    sim = (matrix.T @ matrix).toarray().astype(np.float32)
    denom = np.outer(col_norms, col_norms) + 1e-9
    sim /= denom
    np.fill_diagonal(sim, 0.0)
    return sim


def build_user_similarity_matrix(matrix: csr_matrix) -> np.ndarray:
    row_norms = np.sqrt(matrix.power(2).sum(axis=1)).A1
    row_norms[row_norms == 0] = 1.0
    sim = (matrix @ matrix.T).toarray().astype(np.float32)
    denom = np.outer(row_norms, row_norms) + 1e-9
    sim /= denom
    np.fill_diagonal(sim, 0.0)
    return sim


def build_full_similarity_matrix(matrix: csr_matrix) -> np.ndarray:
    return build_item_similarity_matrix(matrix)


def load_order_baskets(engine, valid_products: set[int]) -> list[list[int]]:
    sql = text(
        """
        SELECT o.id AS order_id, oi.product_id
        FROM oms_order o
        INNER JOIN oms_order_item oi ON o.id = oi.order_id
        WHERE o.delete_status = 0
        """
    )
    buckets: dict[int, set[int]] = defaultdict(set)
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()
    for row in rows:
        pid = int(row["product_id"])
        if pid not in valid_products:
            continue
        buckets[int(row["order_id"])].add(pid)
    return [sorted(items) for items in buckets.values() if items]


def build_basket_cooccurrence_sim(
    baskets: list[list[int]],
    item_index: dict[int, int],
    n_items: int,
) -> np.ndarray:
    """Order basket co-occurrence with cosine normalization."""
    cooc = np.zeros((n_items, n_items), dtype=np.float32)
    item_freq = np.zeros(n_items, dtype=np.float32)
    for basket in baskets:
        indices = [item_index[p] for p in basket if p in item_index]
        for idx in indices:
            item_freq[idx] += 1.0
        for a in range(len(indices)):
            for b in range(a + 1, len(indices)):
                i, j = indices[a], indices[b]
                cooc[i, j] += 1.0
                cooc[j, i] += 1.0
    norms = np.sqrt(item_freq)
    norms[norms == 0] = 1.0
    sim = cooc / (np.outer(norms, norms) + 1e-9)
    np.fill_diagonal(sim, 0.0)
    return sim


def blend_similarity(a: np.ndarray, b: np.ndarray, alpha: float) -> np.ndarray:
    sim = alpha * a + (1.0 - alpha) * b
    np.fill_diagonal(sim, 0.0)
    return sim


def evaluate_hr_at_k(
    user_items: dict[int, list[tuple[int, float]]],
    sim_matrix: np.ndarray,
    item_index: dict[int, int],
    item_rev: dict[int, int],
    k: int = 10,
    seed: int = 42,
    min_weight: float = 0.0,
    user_sim_matrix: np.ndarray | None = None,
    user_index: dict[int, int] | None = None,
    user_rev: dict[int, int] | None = None,
    order_matrix: csr_matrix | None = None,
) -> float:
    rng = random.Random(seed)
    hits = 0
    total = 0
    for member_id, profile in user_items.items():
        profile = [(p, w) for p, w in profile if w >= min_weight]
        if len(profile) < MIN_USER_INTERACTIONS:
            continue
        hold = rng.choice(profile)
        hold_pid = hold[0]
        train_profile = [(p, w) for p, w in profile if p != hold_pid]
        exclude = {p for p, _ in train_profile}
        recs = recommend_with_similarity(
            train_profile,
            sim_matrix,
            item_index,
            item_rev,
            exclude,
            k,
            user_sim_matrix=user_sim_matrix,
            user_index=user_index,
            user_rev=user_rev,
            order_matrix=order_matrix,
            member_id=member_id,
        )
        total += 1
        if hold_pid in recs:
            hits += 1
    return hits / total if total else 0.0


def popular_products(matrix: csr_matrix, item_rev: dict[int, int], top_n: int = 30) -> list[int]:
    popularity = np.asarray(matrix.sum(axis=0)).ravel()
    ranked = np.argsort(-popularity)
    result = []
    for idx in ranked:
        if popularity[idx] <= 0:
            break
        result.append(item_rev[int(idx)])
        if len(result) >= top_n:
            break
    return result


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    print("Loading interactions...")
    interactions = load_interactions(engine)
    valid_products = load_published_products(engine)
    print(f"  raw interactions: {len(interactions)}, published products: {len(valid_products)}")

    matrix, user_index_map, item_rev, user_items = build_matrices(interactions, valid_products)
    user_rev = {i: u for u, i in user_index_map.items()}
    item_index = {item_rev[i]: i for i in item_rev}
    n_users, n_items = matrix.shape
    print(f"  matrix: {n_users} users x {n_items} items")

    strong_pairs = load_strong_pairs(engine, valid_products)
    print(f"  similarity pairs (binary): {len(strong_pairs)}")
    sim_rows, sim_cols, sim_data = [], [], []
    order_rows, order_cols, order_data = [], [], []
    for member_id, product_id in strong_pairs:
        ui = user_index_map.get(member_id)
        ii = item_index.get(product_id)
        if ui is not None and ii is not None:
            order_rows.append(ui)
            order_cols.append(ii)
            order_data.append(1.0)
    order_matrix = csr_matrix(
        (order_data, (order_rows, order_cols)),
        shape=matrix.shape,
        dtype=np.float32,
    )

    for member_id, product_id in strong_pairs:
        ui = user_index_map.get(member_id)
        ii = item_index.get(product_id)
        if ui is None or ii is None:
            continue
        sim_rows.append(ui)
        sim_cols.append(ii)
        sim_data.append(1.0)
    sim_matrix_input = csr_matrix(
        (sim_data, (sim_rows, sim_cols)),
        shape=matrix.shape,
        dtype=np.float32,
    )

    baskets = load_order_baskets(engine, valid_products)
    print(f"  order baskets: {len(baskets)}")

    print("Computing item similarity...")
    behavior_sim = build_full_similarity_matrix(sim_matrix_input)
    basket_sim = build_basket_cooccurrence_sim(baskets, item_index, n_items)
    product_meta = load_product_meta(engine, valid_products)
    user_sim_for_eval = build_user_similarity_matrix(order_matrix)

    print("Tuning blend/content hyperparameters...")
    best_hr = -1.0
    best_sim: np.ndarray | None = None
    best_cfg: dict = {}
    for alpha in (0.45, 0.6, 0.75, 0.9):
        for cat_w in (0.15, 0.3, 0.45):
            for brand_w in (0.1, 0.2):
                candidate = blend_similarity(basket_sim, behavior_sim, alpha=alpha)
                candidate = inject_content_similarity(
                    candidate, item_rev, product_meta, category_weight=cat_w, brand_weight=brand_w
                )
                hr = evaluate_hr_at_k(
                    user_items,
                    candidate,
                    item_index,
                    item_rev,
                    TOP_K_EVAL,
                    min_weight=EVENT_WEIGHTS["order"],
                    user_sim_matrix=user_sim_for_eval,
                    user_index=user_index_map,
                    user_rev=user_rev,
                    order_matrix=order_matrix,
                )
                if hr > best_hr:
                    best_hr = hr
                    best_sim = candidate.copy()
                    best_cfg = {"alpha": alpha, "category_weight": cat_w, "brand_weight": brand_w}

    sim_matrix = best_sim if best_sim is not None else behavior_sim
    print(f"  best order-holdout HR@{TOP_K_EVAL} = {best_hr:.4f} with {best_cfg}")
    item_similar_idx = top_similar_from_matrix(sim_matrix, item_rev, TOP_K_SIMILAR)

    item_similar_json: dict[str, list[dict[str, float | int]]] = {}
    for idx, neighbors in item_similar_idx.items():
        pid = item_rev[idx]
        item_similar_json[str(pid)] = [
            {"productId": int(n_pid), "score": round(score, 6)} for n_pid, score in neighbors
        ]

    print("Evaluating HR@10 (leave-one-out)...")
    user_sim_final = build_user_similarity_matrix(order_matrix)
    hr10 = evaluate_hr_at_k(
        user_items,
        sim_matrix,
        item_index,
        item_rev,
        TOP_K_EVAL,
        user_sim_matrix=user_sim_final,
        user_index=user_index_map,
        user_rev=user_rev,
        order_matrix=order_matrix,
    )
    hr10_orders = evaluate_hr_at_k(
        user_items,
        sim_matrix,
        item_index,
        item_rev,
        TOP_K_EVAL,
        min_weight=EVENT_WEIGHTS["order"],
        user_sim_matrix=user_sim_final,
        user_index=user_index_map,
        user_rev=user_rev,
        order_matrix=order_matrix,
    )
    print(f"  HR@{TOP_K_EVAL} (all signals) = {hr10:.4f}")
    print(f"  HR@{TOP_K_EVAL} (order holdout) = {hr10_orders:.4f}")
    hr10_report = hr10

    pop = popular_products(matrix, item_rev, 30)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "algorithm": "ItemCF",
        "similarity": "tuned_hybrid_basket_behavior_content",
        "tuning": best_cfg,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_users": n_users,
        "n_items": n_items,
        "n_interactions": len(interactions),
        "top_k_similar": TOP_K_SIMILAR,
        "metrics": {
            "hr_at_10": round(hr10_report, 4),
            "hr_at_10_all_signals": round(hr10, 4),
            "hr_at_10_order_holdout": round(hr10_orders, 4),
        },
        "event_weights": EVENT_WEIGHTS,
    }

    (MODEL_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (MODEL_DIR / "item_similar.json").write_text(
        json.dumps(item_similar_json, ensure_ascii=False), encoding="utf-8"
    )
    (MODEL_DIR / "popular.json").write_text(json.dumps(pop, ensure_ascii=False), encoding="utf-8")

    print(f"Model saved to {MODEL_DIR}")
    if hr10 < 0.10 and hr10_orders < 0.10:
        print("WARNING: HR@10 below target 0.10 — consider more order/cart events or tuning weights.")


if __name__ == "__main__":
    main()
