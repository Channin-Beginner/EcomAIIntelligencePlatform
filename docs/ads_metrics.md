# ADS 指标口径说明（阶段三）

> 运营端 `ecom-ops-web` 与 `GET /ops/dashboard/*` 接口统一读取本口径。  
> 数据窗口：**2025-01-01 00:00:00 ~ 2026-01-01 00:00:00**（与造数脚本一致）。

## 1. ADS 表一览

| ADS 表 | 刷新来源 | 大屏模块 |
|--------|----------|----------|
| `ads_order_daily` | `oms_order`、`ums_member` | 核心 KPI、近 30 日趋势 |
| `ads_order_hourly` | `oms_order` | 24 小时销售曲线 |
| `ads_funnel_daily` | `ecom_event_log` | 转化漏斗 |
| `ads_member_active` | `ecom_event_log` | UV/PV 活跃 |
| `ads_region_sales` | `oms_order.receiver_province` | 地域销售 TOP |
| `ads_product_top` | `oms_order` + `oms_order_item` | 热销商品 TOP10 |
| `ads_order_status` | `oms_order.status` | 订单状态分布 |

## 2. 指标定义

### 2.1 订单与 GMV

- **订单数**：`oms_order` 中 `delete_status = 0` 的订单条数。
- **GMV**：上述订单 `pay_amount` 之和（实付金额）。
- **已支付订单**：`status >= 1`（待发货及之后状态）。

### 2.2 漏斗（`ecom_event_log`）

| 阶段 | event_type |
|------|------------|
| 浏览 PV | `pv` |
| 点击 | `click` |
| 加购 | `cart` |
| 收藏 | `fav` |
| 下单事件 | `order` |

### 2.3 活跃

- **UV**：当日 `member_id` 与 `session_id` 合并去重后的访客数。
- **PV**：当日 `event_type = 'pv'` 事件数。
- **活跃会员**：当日有行为且 `member_id` 非空的去重会员数。

### 2.4 地域

- 按 `receiver_province` 聚合；空值记为「未知」。

### 2.5 热销商品

- 按当日订单明细 `product_real_price * product_quantity` 汇总 GMV，取 TOP10。

### 2.6 订单状态

| status | 名称 |
|--------|------|
| 0 | 待付款 |
| 1 | 待发货 |
| 2 | 已发货 |
| 3 | 已完成 |
| 4 | 已关闭 |
| 5 | 无效订单 |

## 3. 参考日期（refDate）

造数为历史 2025 年数据，大屏使用 **参考日期** 而非系统当天：

- 默认取 `ads_order_daily` 中最新 `stat_date`。
- 前端可切换 `2025-01-01` ~ `2025-12-31` 任意日期。
- 「今日」= refDate；「本周」= refDate 所在自然周；「本月」= refDate 所在自然月。

## 4. 刷新与验收

```powershell
# 1. 创建 ADS 表（首次）
mysql -u root -p mall < sql\ads\ads_tables.sql

# 2. 从 OLTP 刷新 ADS
python scripts\ads\refresh_ads.py

# 或通过 API
curl -X POST http://127.0.0.1:8081/ops/ads/refresh
```

**验收 KPI（阶段三）**

- 口径偏差 ≤ 1%：ADS 汇总与 OLTP 同条件聚合结果对比。
- 首屏 ≤ 3s：运营端并行请求 8 个 dashboard 接口。

## 5. API 列表

| 接口 | 说明 |
|------|------|
| `GET /ops/dashboard/overview` | 日/周/月 KPI |
| `GET /ops/dashboard/order-hourly` | 24h 曲线 |
| `GET /ops/dashboard/funnel` | 漏斗 |
| `GET /ops/dashboard/member-active` | UV/PV 趋势 |
| `GET /ops/dashboard/region-sales` | 地域 TOP |
| `GET /ops/dashboard/order-trend` | 日订单趋势 |
| `GET /ops/dashboard/product-top` | 热销 TOP |
| `GET /ops/dashboard/order-status` | 状态分布 |
| `GET /ops/ads/meta` | ADS 元信息 |
| `POST /ops/ads/refresh` | 触发 ADS 全量刷新 |
