"""
Phase-2 seed CSV generator for EcomAI Intelligence Platform.

Generates relational CSV bundles under 灌注数据/ — does NOT import to DB.
Time window: 2025-01-01 00:00:00 ~ 2026-01-01 00:00:00 (exclusive end).

Run: python scripts/seed/generate_csv_data.py
"""

from __future__ import annotations

import csv
import json
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "灌注数据"

# --- scale (doc §4 / §5 phase-2 KPI) ---
NUM_MEMBERS = 3000
NUM_NEW_PRODUCTS = 320          # + existing mall SKUs → total SKU ≥ 500
NUM_ORDERS = 10000
NUM_COMMENTS = 5000
NUM_CART_ITEMS = 15000          # oms_cart_item rows; + cart events in ecom_event_log ≥ 50k total (doc §4.2)
MIN_CART_ROWS_COMBINED = 50000  # oms_cart_item + ecom_event_log(cart) combined
NUM_EVENTS = 200000

MEMBER_ID_START = 10001
PRODUCT_ID_START = 1000
SKU_ID_START = 1000
ORDER_ID_START = 100001
ORDER_ITEM_ID_START = 100001
ADDRESS_ID_START = 10001
CART_ID_START = 100001
COMMENT_ID_START = 1
EVENT_ID_START = 1

TIME_START = datetime(2025, 1, 1, 0, 0, 0)
TIME_END = datetime(2026, 1, 1, 0, 0, 0)

# mall bcrypt for password "123456" (same family as demo accounts)
PWD_HASH = "$2a$10$NZ5o7r2E.ayT2ZoxgjlI.eJ6OEYqjH7INR/F.mXDbjZJi9HF0YCVG"

DIGITAL_BRANDS = [
    (3, "华为", 19, "手机通讯"),
    (6, "小米", 19, "手机通讯"),
    (51, "苹果", 19, "手机通讯"),
    (21, "OPPO", 19, "手机通讯"),
    (2, "三星", 55, "硬盘"),
    (6, "小米", 54, "笔记本"),
    (51, "苹果", 53, "平板电脑"),
    (6, "小米", 35, "电视"),
]

EXISTING_PRODUCT_IDS = list(range(26, 46))  # mall digital catalog already online

CITIES = [
    ("广东省", "深圳市", "南山区"),
    ("广东省", "广州市", "天河区"),
    ("北京市", "北京城区", "朝阳区"),
    ("上海市", "上海城区", "浦东新区"),
    ("浙江省", "杭州市", "西湖区"),
    ("江苏省", "南京市", "鼓楼区"),
    ("四川省", "成都市", "武侯区"),
    ("湖北省", "武汉市", "洪山区"),
    ("福建省", "厦门市", "思明区"),
    ("陕西省", "西安市", "雁塔区"),
]

PRODUCT_TEMPLATES = [
    "5G智能手机", "无线蓝牙耳机", "智能手表", "平板电脑", "轻薄笔记本",
    "4K智能电视", "固态硬盘", "游戏显卡", "机械键盘", "电竞显示器",
    "移动电源", "氮化镓充电器", "家用路由器", "智能音箱", "运动相机",
]

COMMENT_SAMPLES = [
    "物流很快，包装完好，数码产品正品无疑。",
    "性价比不错，续航比预期好一些，推荐购买。",
    "屏幕显示效果清晰，系统流畅，满意。",
    "做工精致，手感很好，符合品牌水准。",
    "活动价入手很划算，客服响应也及时。",
    "使用一周暂无问题，后续再追评。",
    "音质/画质都不错，家人很喜欢。",
    "发货速度快，发票齐全，企业采购方便。",
]


@dataclass
class Product:
    id: int
    brand_id: int
    brand_name: str
    category_id: int
    category_name: str
    name: str
    product_sn: str
    price: float
    pic: str
    is_hot: bool = False


@dataclass
class Sku:
    id: int
    product_id: int
    sku_code: str
    price: float
    sp_data: str


@dataclass
class Member:
    id: int
    username: str
    nickname: str
    phone: str
    create_time: datetime
    city: str
    province: str


@dataclass
class Address:
    id: int
    member_id: int
    name: str
    phone: str
    province: str
    city: str
    region: str
    detail: str


@dataclass
class Order:
    id: int
    member_id: int
    order_sn: str
    create_time: datetime
    username: str
    pay_amount: float
    total_amount: float
    status: int
    receiver_name: str
    receiver_phone: str
    receiver_province: str
    receiver_city: str
    receiver_region: str
    receiver_detail: str
    payment_time: datetime | None
    receive_time: datetime | None = None


@dataclass
class OrderItem:
    id: int
    order_id: int
    order_sn: str
    product_id: int
    sku_id: int
    product_name: str
    product_brand: str
    product_sn: str
    product_price: float
    quantity: int


def clamp_time(dt: datetime, rng: random.Random | None = None) -> datetime:
    r = rng or random
    if dt < TIME_START:
        return TIME_START + timedelta(seconds=r.randint(0, 3600))
    if dt >= TIME_END:
        return TIME_END - timedelta(seconds=r.randint(1, 3600))
    return dt


def rand_time(rng: random.Random, boost_weekend: bool = False) -> datetime:
    span = int((TIME_END - TIME_START).total_seconds())
    offset = rng.randint(0, span - 1)
    dt = TIME_START + timedelta(seconds=offset)
    if boost_weekend and dt.weekday() >= 5:
        if rng.random() < 0.35:
            dt = dt.replace(hour=rng.randint(10, 22))
    return dt


def weighted_order_time(rng: random.Random) -> datetime:
    """Weekend orders slightly higher (doc §4.4)."""
    for _ in range(8):
        dt = rand_time(rng)
        if dt.weekday() >= 5:
            if rng.random() < 0.55:
                return dt
        else:
            if rng.random() < 0.45:
                return dt
    return rand_time(rng)


def fmt_dt(dt: datetime | None) -> str:
    return "" if dt is None else dt.strftime("%Y-%m-%d %H:%M:%S")


def write_csv(path: Path, headers: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def build_catalog(rng: random.Random) -> tuple[list[Product], list[Sku], list[int]]:
    products: list[Product] = []
    skus: list[Sku] = []
    hot_product_ids: list[int] = []

    for i in range(NUM_NEW_PRODUCTS):
        pid = PRODUCT_ID_START + i
        brand_id, brand_name, cat_id, cat_name = DIGITAL_BRANDS[i % len(DIGITAL_BRANDS)]
        tmpl = PRODUCT_TEMPLATES[i % len(PRODUCT_TEMPLATES)]
        series = 2025 + (i % 3)
        name = f"{brand_name} {tmpl} {series}款"
        base_price = rng.choice([299, 499, 699, 999, 1299, 1999, 2699, 3599, 4999, 5999])
        price = float(base_price + rng.randint(0, 9) * 10)
        is_hot = i < max(1, int(NUM_NEW_PRODUCTS * 0.05))
        p = Product(
            id=pid,
            brand_id=brand_id,
            brand_name=brand_name,
            category_id=cat_id,
            category_name=cat_name,
            name=name,
            product_sn=f"SEED{pid:06d}",
            price=price,
            pic="http://macro-oss.oss-cn-shenzhen.aliyuncs.com/mall/images/20180615/xiaomi.jpg",
            is_hot=is_hot,
        )
        products.append(p)
        if is_hot:
            hot_product_ids.append(pid)

        sku_count = 2 if rng.random() < 0.25 else 1
        for s in range(sku_count):
            sid = SKU_ID_START + len(skus)
            cap = rng.choice(["128G", "256G", "512G", "64G"])
            color = rng.choice(["黑色", "白色", "蓝色", "银色"])
            sp = json.dumps([{"key": "颜色", "value": color}, {"key": "容量", "value": cap}], ensure_ascii=False)
            skus.append(
                Sku(
                    id=sid,
                    product_id=pid,
                    sku_code=f"SEED{pid:06d}{s+1:02d}",
                    price=price + s * 200,
                    sp_data=sp,
                )
            )

    # existing mall products participate in transactions & hot SKU pool
    for ep in EXISTING_PRODUCT_IDS:
        if ep in (26, 27, 37, 40, 41, 42):
            hot_product_ids.append(ep)

    return products, skus, hot_product_ids


def pick_sku_for_product(sku_by_product: dict[int, list[Sku]], product_id: int, rng: random.Random) -> Sku:
    if product_id in sku_by_product:
        return rng.choice(sku_by_product[product_id])
    # fallback: map existing mall product → representative sku ids from mall.sql
    fallback = {26: 110, 27: 98, 28: 102, 29: 106, 37: 201, 38: 213, 39: 217, 40: 221, 41: 225, 42: 229, 44: 235, 45: 239}
    sid = fallback.get(product_id, 98)
    return Sku(id=sid, product_id=product_id, sku_code=f"MALL{product_id}", price=1999.0, sp_data="[]")


def main() -> None:
    rng = random.Random(20250101)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    products, skus, hot_product_ids = build_catalog(rng)
    sku_by_product: dict[int, list[Sku]] = defaultdict(list)
    product_by_id = {p.id: p for p in products}
    for s in skus:
        sku_by_product[s.product_id].append(s)

    all_product_ids = EXISTING_PRODUCT_IDS + [p.id for p in products]

    # --- members + addresses (bundle A) ---
    members: list[Member] = []
    addresses: list[Address] = []
    member_rows: list[list] = []
    address_rows: list[list] = []

    for i in range(NUM_MEMBERS):
        mid = MEMBER_ID_START + i
        username = f"seed_user_{mid}"
        nickname = f"用户{mid}"
        phone = f"199{mid:08d}"[-11:]
        reg_time = rand_time(rng)
        prov, city, region = rng.choice(CITIES)
        m = Member(mid, username, nickname, phone, reg_time, city, prov)
        members.append(m)
        member_rows.append([
            mid, 4, username, PWD_HASH, nickname, phone, 1, fmt_dt(reg_time),
            "", rng.choice([0, 1, 2]), "", prov, "", "", 1,
            rng.randint(100, 5000), rng.randint(0, 2000), 0, 0,
        ])
        aid = ADDRESS_ID_START + i
        addr = Address(aid, mid, nickname, phone, prov, city, region, f"{region}科技园路{rng.randint(1, 200)}号")
        addresses.append(addr)
        address_rows.append([aid, mid, nickname, phone, 1, "518000", prov, city, region, addr.detail])

    write_csv(
        OUT_DIR / "ums_member.csv",
        [
            "id", "member_level_id", "username", "password", "nickname", "phone", "status",
            "create_time", "icon", "gender", "birthday", "city", "job", "personalized_signature",
            "source_type", "integration", "growth", "luckey_count", "history_integration",
        ],
        member_rows,
    )
    write_csv(
        OUT_DIR / "ums_member_receive_address.csv",
        ["id", "member_id", "name", "phone_number", "default_status", "post_code", "province", "city", "region", "detail_address"],
        address_rows,
    )

    # --- products + skus (bundle B) ---
    product_rows = []
    for p in products:
        product_rows.append([
            p.id, p.brand_id, p.category_id, 0, 3, p.name, p.pic, p.product_sn,
            0, 1, 1 if rng.random() < 0.3 else 0, 1 if p.is_hot else 0, 1,
            rng.randint(0, 200), 0, p.price, "", 0, 0, 0,
            f"{p.name} 官方正品", "", p.price * 1.1, 500, 10, "件", 0,
            0, "1,2,3", p.name, "", "", "", "", "", "", "", "", "", 0,
            p.brand_name, p.category_name,
        ])
    write_csv(
        OUT_DIR / "pms_product.csv",
        [
            "id", "brand_id", "product_category_id", "feight_template_id", "product_attribute_category_id",
            "name", "pic", "product_sn", "delete_status", "publish_status", "new_status", "recommand_status",
            "verify_status", "sort", "sale", "price", "promotion_price", "gift_growth", "gift_point",
            "use_point_limit", "sub_title", "description", "original_price", "stock", "low_stock", "unit",
            "weight", "preview_status", "service_ids", "keywords", "note", "album_pics", "detail_title",
            "detail_desc", "detail_html", "detail_mobile_html", "promotion_start_time", "promotion_end_time",
            "promotion_per_limit", "promotion_type", "brand_name", "product_category_name",
        ],
        product_rows,
    )

    sku_rows = []
    for s in skus:
        sku_rows.append([s.id, s.product_id, s.sku_code, s.price, 300, 10, "", 0, "", 0, s.sp_data])
    write_csv(
        OUT_DIR / "pms_sku_stock.csv",
        ["id", "product_id", "sku_code", "price", "stock", "low_stock", "pic", "sale", "promotion_price", "lock_stock", "sp_data"],
        sku_rows,
    )

    # --- orders + items (bundle C) ---
    orders: list[Order] = []
    order_items: list[OrderItem] = []
    order_rows: list[list] = []
    order_item_rows: list[list] = []
    product_sale_counts: dict[int, int] = defaultdict(int)
    hot_set = set(hot_product_ids)

    member_by_id = {m.id: m for m in members}
    addr_by_member = {a.member_id: a for a in addresses}

    for i in range(NUM_ORDERS):
        oid = ORDER_ID_START + i
        m = rng.choice(members)
        addr = addr_by_member[m.id]
        create_time = weighted_order_time(rng)

        # 5% hot SKUs ~ 40% GMV
        if rng.random() < 0.40:
            product_id = rng.choice(hot_product_ids)
        else:
            product_id = rng.choice(all_product_ids)

        sku = pick_sku_for_product(sku_by_product, product_id, rng)
        qty = rng.choice([1, 1, 1, 2])
        unit_price = sku.price
        if product_id in product_by_id:
            unit_price = product_by_id[product_id].price
        total = round(unit_price * qty, 2)
        pay = total

        status = rng.choices([3, 2, 1, 0, 4], weights=[72, 10, 8, 7, 3])[0]
        pay_type = rng.choice([1, 2]) if status >= 1 else 0
        payment_time = create_time + timedelta(minutes=rng.randint(1, 45)) if status >= 1 else None
        delivery_time = (payment_time + timedelta(hours=rng.randint(4, 48))) if status >= 2 and payment_time else None
        receive_time = (delivery_time + timedelta(days=rng.randint(1, 5))) if status >= 3 and delivery_time else None

        order_sn = create_time.strftime("%Y%m%d") + f"{i+1:06d}"
        o = Order(
            id=oid,
            member_id=m.id,
            order_sn=order_sn,
            create_time=create_time,
            username=m.username,
            pay_amount=pay,
            total_amount=total,
            status=status,
            receiver_name=addr.name,
            receiver_phone=addr.phone,
            receiver_province=addr.province,
            receiver_city=addr.city,
            receiver_region=addr.region,
            receiver_detail=addr.detail,
            payment_time=payment_time,
            receive_time=receive_time,
        )
        orders.append(o)

        pname = product_by_id[product_id].name if product_id in product_by_id else f"商品{product_id}"
        pbrand = product_by_id[product_id].brand_name if product_id in product_by_id else "品牌"
        psn = product_by_id[product_id].product_sn if product_id in product_by_id else f"MALL{product_id}"

        oi_id = ORDER_ITEM_ID_START + i
        oi = OrderItem(oi_id, oid, order_sn, product_id, sku.id, pname, pbrand, psn, unit_price, qty)
        order_items.append(oi)
        product_sale_counts[product_id] += qty

        order_rows.append([
            oid, m.id, "", order_sn, fmt_dt(create_time), m.username, total, pay, 0, 0, 0, 0, 0,
            pay_type, 0, status, 0, "顺丰快递" if status >= 2 else "", f"SF{oid}" if status >= 2 else "",
            15, int(pay), int(pay), "无优惠", 0, "", "", "", "", addr.name, addr.phone, "518000",
            addr.province, addr.city, addr.region, addr.detail, "", 1 if status == 3 else 0, 0, 0,
            fmt_dt(payment_time), fmt_dt(delivery_time), fmt_dt(receive_time), "", "",
        ])
        cat_id = product_by_id[product_id].category_id if product_id in product_by_id else 19
        real_amount = round(unit_price * qty, 2)
        order_item_rows.append([
            oi_id, oid, order_sn, product_id, "", pname, pbrand, psn,
            unit_price, qty, sku.id, sku.sku_code, cat_id,
            "无优惠", 0, 0, 0, real_amount, int(real_amount), int(real_amount), sku.sp_data,
        ])

    write_csv(
        OUT_DIR / "oms_order.csv",
        [
            "id", "member_id", "coupon_id", "order_sn", "create_time", "member_username", "total_amount",
            "pay_amount", "freight_amount", "promotion_amount", "integration_amount", "coupon_amount",
            "discount_amount", "pay_type", "source_type", "status", "order_type", "delivery_company",
            "delivery_sn", "auto_confirm_day", "integration", "growth", "promotion_info", "bill_type",
            "bill_header", "bill_content", "bill_receiver_phone", "bill_receiver_email", "receiver_name",
            "receiver_phone", "receiver_post_code", "receiver_province", "receiver_city", "receiver_region",
            "receiver_detail_address", "note", "confirm_status", "delete_status", "use_integration",
            "payment_time", "delivery_time", "receive_time", "comment_time", "modify_time",
        ],
        order_rows,
    )
    write_csv(
        OUT_DIR / "oms_order_item.csv",
        [
            "id", "order_id", "order_sn", "product_id", "product_pic", "product_name", "product_brand",
            "product_sn", "product_price", "product_quantity", "product_sku_id", "product_sku_code",
            "product_category_id", "promotion_name", "promotion_amount", "coupon_amount",
            "integration_amount", "real_amount", "gift_integration", "gift_growth", "product_attr",
        ],
        order_item_rows,
    )

    # --- comments on completed orders (bundle D) ---
    completed = [o for o in orders if o.status == 3]
    rng.shuffle(completed)
    comment_targets = completed[:NUM_COMMENTS]
    comment_rows = []
    for idx, o in enumerate(comment_targets):
        oi = order_items[o.id - ORDER_ID_START]
        m = member_by_id[o.member_id]
        ctime = (o.receive_time or o.create_time) + timedelta(hours=rng.randint(2, 72))
        comment_rows.append([
            COMMENT_ID_START + idx, oi.product_id, m.nickname, oi.product_name,
            rng.choice([4, 5, 5, 5, 3]), f"10.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}",
            fmt_dt(ctime), 1, "{}", rng.randint(0, 20), rng.randint(10, 500),
            rng.choice(COMMENT_SAMPLES), "", "", 0,
        ])
    write_csv(
        OUT_DIR / "pms_comment.csv",
        [
            "id", "product_id", "member_nick_name", "product_name", "star", "member_ip", "create_time",
            "show_status", "product_attribute", "collect_couont", "read_count", "content", "pics",
            "member_icon", "replay_count",
        ],
        comment_rows,
    )

    # --- cart items (bundle E) ---
    cart_rows = []
    cart_event_pool: list[tuple[int, int, int, datetime]] = []
    for i in range(NUM_CART_ITEMS):
        cid = CART_ID_START + i
        m = rng.choice(members)
        product_id = rng.choice(all_product_ids)
        sku = pick_sku_for_product(sku_by_product, product_id, rng)
        qty = rng.randint(1, 3)
        ctime = rand_time(rng)
        pname = product_by_id[product_id].name if product_id in product_by_id else f"商品{product_id}"
        pbrand = product_by_id[product_id].brand_name if product_id in product_by_id else "品牌"
        psn = product_by_id[product_id].product_sn if product_id in product_by_id else f"MALL{product_id}"
        cat = product_by_id[product_id].category_id if product_id in product_by_id else 19
        deleted = 1 if rng.random() < 0.85 else 0
        cart_rows.append([
            cid, product_id, sku.id, m.id, qty, sku.price, "", pname, pname, sku.sku_code,
            m.nickname, fmt_dt(ctime), "", deleted, cat, pbrand, psn, sku.sp_data,
        ])
        cart_event_pool.append((m.id, product_id, cid, ctime))

    write_csv(
        OUT_DIR / "oms_cart_item.csv",
        [
            "id", "product_id", "product_sku_id", "member_id", "quantity", "price", "product_pic",
            "product_name", "product_sub_title", "product_sku_code", "member_nickname", "create_date",
            "modify_date", "delete_status", "product_category_id", "product_brand", "product_sn", "product_attr",
        ],
        cart_rows,
    )

    # --- ecom_event_log (bundle F) ---
    event_rows: list[list] = []
    eid = EVENT_ID_START

    def add_event(member_id: int, product_id: int, etype: str, etime: datetime, session_id: str, extra: dict | None = None):
        nonlocal eid
        event_rows.append([
            eid, member_id, product_id, etype, fmt_dt(etime), session_id, "seed",
            f"/product/{product_id}", json.dumps(extra or {}, ensure_ascii=False),
        ])
        eid += 1

    # order-linked journeys (timestamps clamped to doc time window)
    for o in orders:
        oi = order_items[o.id - ORDER_ID_START]
        sid = uuid.uuid4().hex[:16]
        t0 = clamp_time(o.create_time - timedelta(days=rng.randint(0, 7), hours=rng.randint(1, 10)), rng)
        add_event(o.member_id, oi.product_id, "pv", t0, sid)
        add_event(o.member_id, oi.product_id, "click", clamp_time(t0 + timedelta(minutes=rng.randint(1, 5)), rng), sid)
        if rng.random() < 0.35:
            add_event(o.member_id, oi.product_id, "fav", clamp_time(t0 + timedelta(minutes=rng.randint(5, 20)), rng), sid)
        if rng.random() < 0.55:
            add_event(o.member_id, oi.product_id, "cart", clamp_time(t0 + timedelta(minutes=rng.randint(10, 40)), rng), sid)
        if o.status >= 1:
            add_event(o.member_id, oi.product_id, "order", o.create_time, sid, {"order_id": o.id})

    # cart events from oms_cart_item bundle
    for mid, pid, _cid, ctime in cart_event_pool:
        add_event(mid, pid, "cart", ctime, uuid.uuid4().hex[:16])

    # extra cart events until oms_cart_item + cart events meet doc §4.2 (≥50k combined)
    cart_event_count = sum(1 for r in event_rows if r[3] == "cart")
    while cart_event_count + len(cart_rows) < MIN_CART_ROWS_COMBINED:
        m = rng.choice(members)
        pid = rng.choice(all_product_ids)
        add_event(m.id, pid, "cart", rand_time(rng), uuid.uuid4().hex[:16])
        cart_event_count += 1

    # fill browsing noise to reach NUM_EVENTS
    while len(event_rows) < NUM_EVENTS:
        m = rng.choice(members)
        pid = rng.choice(all_product_ids)
        etype = rng.choices(["pv", "click", "fav"], weights=[50, 35, 15])[0]
        add_event(m.id, pid, etype, rand_time(rng), uuid.uuid4().hex[:16])

    event_rows = event_rows[:NUM_EVENTS]
    write_csv(
        OUT_DIR / "ecom_event_log.csv",
        ["event_id", "member_id", "product_id", "event_type", "event_time", "session_id", "source", "page_path", "extra_json"],
        event_rows,
    )

    # --- sale update for products (bundle G) ---
    sale_rows = [[pid, cnt] for pid, cnt in sorted(product_sale_counts.items()) if cnt > 0]
    write_csv(OUT_DIR / "pms_product_sale_update.csv", ["product_id", "sale_increment"], sale_rows)

    sku_sale_rows = []
    for oi in order_items:
        sku_sale_rows.append([oi.sku_id, oi.quantity])
    # aggregate
    sku_agg: dict[int, int] = defaultdict(int)
    for sid, q in sku_sale_rows:
        sku_agg[sid] += q
    write_csv(
        OUT_DIR / "pms_sku_stock_sale_update.csv",
        ["sku_id", "sale_increment"],
        [[k, v] for k, v in sorted(sku_agg.items())],
    )

    # relation index for import validation (one row per order bundle)
    relation_rows = []
    for o in orders:
        oi = order_items[o.id - ORDER_ID_START]
        addr = addr_by_member[o.member_id]
        relation_rows.append([
            o.id, o.member_id, addr.id, oi.product_id, oi.sku_id, oi.id, o.order_sn, fmt_dt(o.create_time),
        ])
    write_csv(
        OUT_DIR / "_relation_index.csv",
        ["order_id", "member_id", "address_id", "product_id", "sku_id", "order_item_id", "order_sn", "create_time"],
        relation_rows,
    )

    # manifest
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "time_window": {"start": fmt_dt(TIME_START), "end_exclusive": fmt_dt(TIME_END)},
        "id_ranges": {
            "member_id": [MEMBER_ID_START, MEMBER_ID_START + NUM_MEMBERS - 1],
            "product_id_new": [PRODUCT_ID_START, PRODUCT_ID_START + NUM_NEW_PRODUCTS - 1],
            "order_id": [ORDER_ID_START, ORDER_ID_START + NUM_ORDERS - 1],
        },
        "row_counts": {
            "ums_member": len(member_rows),
            "ums_member_receive_address": len(address_rows),
            "pms_product": len(product_rows),
            "pms_sku_stock": len(sku_rows),
            "oms_order": len(order_rows),
            "oms_order_item": len(order_item_rows),
            "pms_comment": len(comment_rows),
            "oms_cart_item": len(cart_rows),
            "ecom_event_log": len(event_rows),
            "pms_product_sale_update": len(sale_rows),
        },
        "import_order": [
            "ums_member.csv",
            "ums_member_receive_address.csv",
            "pms_product.csv",
            "pms_sku_stock.csv",
            "oms_order.csv",
            "oms_order_item.csv",
            "pms_comment.csv",
            "oms_cart_item.csv",
            "ecom_event_log.csv",
            "pms_product_sale_update.csv (UPDATE after import)",
            "pms_sku_stock_sale_update.csv (UPDATE after import)",
        ],
        "relation_index": "_relation_index.csv",
        "bundles": {
            "A_member": ["ums_member.csv", "ums_member_receive_address.csv"],
            "B_catalog": ["pms_product.csv", "pms_sku_stock.csv"],
            "C_trade": ["oms_order.csv", "oms_order_item.csv"],
            "D_comment": ["pms_comment.csv"],
            "E_cart": ["oms_cart_item.csv"],
            "F_behavior": ["ecom_event_log.csv"],
            "G_sale_sync": ["pms_product_sale_update.csv", "pms_sku_stock_sale_update.csv"],
        },
        "notes": [
            "Existing mall catalog (product_id 26-45) is referenced by orders/events but not duplicated in pms_product.csv.",
            "All seed rows use 2025-01-01 ~ 2026-01-01 timestamps for dashboard filtering.",
            "Hot SKU ~5% contributes ~40% order GMV per doc §4.4.",
            "_relation_index.csv is for validation only, not imported into MySQL.",
        ],
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated CSV bundle under: {OUT_DIR}")
    for k, v in manifest["row_counts"].items():
        print(f"  {k}: {v:,}")


if __name__ == "__main__":
    main()
