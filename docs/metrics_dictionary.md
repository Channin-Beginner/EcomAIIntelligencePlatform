# 指标字典（智能 BI / NL2SQL）

> 与 `docs/ads_metrics.md`、运营大屏 `GET /ops/dashboard/*` 口径一致。  
> 数据窗口：**2025-01-01 ~ 2026-01-01**。

## 核心指标

| 指标 | 定义 | 主要来源 |
|------|------|----------|
| GMV | 有效订单实付金额合计 `pay_amount` / ADS `gmv` | `ads_order_daily`, `oms_order` |
| 订单数 | `delete_status=0` 的订单条数 | `ads_order_daily`, `oms_order` |
| 已支付订单 | `status >= 1` | `oms_order` |
| UV | 当日访客去重（member_id 与 session_id 合并） | `ads_member_active`, `ecom_event_log` |
| PV | `event_type='pv'` 事件数 | `ads_member_active`, `ecom_event_log` |
| 活跃会员 | 当日有行为且 member_id 非空的去重数 | `ads_member_active` |

## 漏斗阶段（ecom_event_log / ads_funnel_daily）

| 阶段 | event_type / 字段 |
|------|-------------------|
| 浏览 PV | pv / pv_count |
| 点击 | click / click_count |
| 加购 | cart / cart_count |
| 收藏 | fav / fav_count |
| 下单事件 | order / order_event_count |

## 时间语义

- **参考日期 refDate**：大屏与助手默认上下文，如 `2025-06-15`
- **今日** = refDate 当天
- **本周** = refDate 所在自然周（周一至 refDate）
- **本月** = refDate 所在自然月 1 日至 refDate

## 订单状态

| status | 名称 |
|--------|------|
| 0 | 待付款 |
| 1 | 待发货 |
| 2 | 已发货 |
| 3 | 已完成 |
| 4 | 已关闭 |
| 5 | 无效订单 |

## ADS 表用途速查

| 表 | 典型问题 |
|----|----------|
| ads_order_daily | 日 GMV、订单趋势、周/月汇总 |
| ads_order_hourly | 24 小时曲线 |
| ads_funnel_daily | 转化漏斗 |
| ads_member_active | UV/PV 趋势 |
| ads_region_sales | 省份 TOP |
| ads_product_top | 热销商品 |
| ads_order_status | 状态分布饼图 |
