from __future__ import annotations

from typing import Any


def _col(rows: list[dict], key: str) -> list[Any]:
    return [r.get(key) for r in rows]


def build_line_option(title: str, x_data: list[Any], series: list[dict[str, Any]]) -> dict:
    return {
        "title": {"text": title, "left": "center", "textStyle": {"fontSize": 13}},
        "tooltip": {"trigger": "axis"},
        "legend": {"bottom": 0, "textStyle": {"fontSize": 11}},
        "grid": {"left": 48, "right": 24, "top": 40, "bottom": 40},
        "xAxis": {"type": "category", "data": x_data, "axisLabel": {"fontSize": 10}},
        "yAxis": {"type": "value", "axisLabel": {"fontSize": 10}},
        "series": series,
    }


def build_bar_option(title: str, categories: list[str], values: list[Any], horizontal: bool = False) -> dict:
    if horizontal:
        return {
            "title": {"text": title, "left": "center", "textStyle": {"fontSize": 13}},
            "tooltip": {"trigger": "axis"},
            "grid": {"left": 80, "right": 24, "top": 36, "bottom": 28},
            "xAxis": {"type": "value"},
            "yAxis": {"type": "category", "data": categories, "axisLabel": {"fontSize": 10}},
            "series": [{"type": "bar", "data": values, "itemStyle": {"color": "#3b82f6"}}],
        }
    return {
        "title": {"text": title, "left": "center", "textStyle": {"fontSize": 13}},
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 48, "right": 24, "top": 40, "bottom": 60},
        "xAxis": {"type": "category", "data": categories, "axisLabel": {"rotate": 30, "fontSize": 10}},
        "yAxis": {"type": "value"},
        "series": [{"type": "bar", "data": values, "itemStyle": {"color": "#3b82f6"}}],
    }


def build_pie_option(title: str, data: list[dict[str, Any]]) -> dict:
    return {
        "title": {"text": title, "left": "center", "textStyle": {"fontSize": 13}},
        "tooltip": {"trigger": "item"},
        "series": [
            {
                "type": "pie",
                "radius": ["38%", "62%"],
                "center": ["50%", "52%"],
                "data": data,
                "label": {"fontSize": 10},
            }
        ],
    }


def build_funnel_option(title: str, stages: list[dict[str, Any]]) -> dict:
    return {
        "title": {"text": title, "left": "center", "textStyle": {"fontSize": 13}},
        "tooltip": {"trigger": "item"},
        "series": [
            {
                "type": "funnel",
                "left": "12%",
                "width": "76%",
                "sort": "descending",
                "label": {"show": True, "fontSize": 11},
                "data": stages,
            }
        ],
    }


def rows_to_table(rows: list[dict]) -> dict:
    if not rows:
        return {"columns": [], "rows": []}
    columns = list(rows[0].keys())
    table_rows = [[row.get(c) for c in columns] for row in rows]
    return {"columns": columns, "rows": table_rows}


def from_template_overview(data: dict) -> tuple[str, dict, dict | None]:
    ref = data.get("refDate", "")
    today = data.get("today", {})
    answer = (
        f"参考日期 {ref}：当日订单 {today.get('order_count', 0)} 笔，"
        f"GMV ¥{float(today.get('gmv', 0)):,.0f}；"
        f"本周订单 {data.get('week', {}).get('order_count', 0)} 笔，"
        f"本月 GMV ¥{float(data.get('month', {}).get('gmv', 0)):,.0f}。"
    )
    table = {
        "columns": ["维度", "订单数", "GMV", "环比%"],
        "rows": [
            ["今日", today.get("order_count"), today.get("gmv"), today.get("gmvChangePct")],
            ["本周", data.get("week", {}).get("order_count"), data.get("week", {}).get("gmv"), data.get("week", {}).get("gmvChangePct")],
            ["本月", data.get("month", {}).get("order_count"), data.get("month", {}).get("gmv"), data.get("month", {}).get("gmvChangePct")],
        ],
    }
    return answer, {"type": "table", "title": "核心 KPI", "option": None}, table


def from_template_hourly(data: list[dict], ref: str) -> tuple[str, dict, dict | None]:
    hours = [f"{h.get('stat_hour', 0)}:00" for h in data]
    gmv = [float(h.get("gmv") or 0) for h in data]
    answer = f"{ref} 当日 24 小时 GMV 曲线已生成，峰值时段 GMV ¥{max(gmv) if gmv else 0:,.0f}。"
    option = build_line_option(
        "24 小时销售曲线",
        hours,
        [{"name": "GMV", "type": "line", "smooth": True, "data": gmv, "itemStyle": {"color": "#3b82f6"}}],
    )
    return answer, {"type": "line", "title": "24 小时销售曲线", "option": option}, None


def from_template_funnel(data: dict) -> tuple[str, dict, dict | None]:
    stages = data.get("stages", [])
    answer = "转化漏斗：" + " → ".join(f"{s['name']} {s['value']}" for s in stages)
    option = build_funnel_option("转化漏斗", stages)
    return answer, {"type": "funnel", "title": "转化漏斗", "option": option}, None


def from_template_member(data: dict) -> tuple[str, dict, dict | None]:
    latest = data.get("latest", {})
    trend = data.get("trend", [])
    answer = f"当日 UV {latest.get('uv', 0)}，PV {latest.get('pv', 0)}，活跃会员 {latest.get('active_member_count', 0)}。"
    dates = [str(t.get("stat_date", ""))[:10] for t in trend]
    option = build_line_option(
        "UV/PV 趋势",
        dates,
        [
            {"name": "UV", "type": "line", "smooth": True, "data": [t.get("uv", 0) for t in trend]},
            {"name": "PV", "type": "line", "smooth": True, "data": [t.get("pv", 0) for t in trend]},
        ],
    )
    return answer, {"type": "line", "title": "UV/PV 趋势", "option": option}, None


def from_template_regions(data: dict) -> tuple[str, dict, dict | None]:
    regions = data.get("regions", [])
    names = [r.get("province", "") for r in regions]
    gmv = [float(r.get("gmv") or 0) for r in regions]
    answer = f"地域销售 TOP{len(regions)}：榜首 {names[0] if names else '—'}，GMV ¥{gmv[0] if gmv else 0:,.0f}。"
    option = build_bar_option("地域销售 TOP", names, gmv, horizontal=True)
    return answer, {"type": "bar", "title": "地域销售", "option": option}, None


def from_template_trend(data: dict) -> tuple[str, dict, dict | None]:
    trend = data.get("trend", [])
    dates = [str(t.get("stat_date", ""))[:10] for t in trend]
    gmv = [float(t.get("gmv") or 0) for t in trend]
    answer = f"近 {len(trend)} 日 GMV 趋势，合计 ¥{sum(gmv):,.0f}。"
    option = build_line_option(
        "订单趋势",
        dates,
        [
            {"name": "GMV", "type": "line", "smooth": True, "areaStyle": {}, "data": gmv},
            {"name": "订单", "type": "line", "smooth": True, "yAxisIndex": 0, "data": [t.get("order_count", 0) for t in trend]},
        ],
    )
    return answer, {"type": "line", "title": "近 30 日趋势", "option": option}, None


def from_template_products(data: dict) -> tuple[str, dict, dict | None]:
    products = data.get("products", [])
    names = [p.get("product_name", "")[:12] for p in products]
    gmv = [float(p.get("gmv") or 0) for p in products]
    top = products[0].get("product_name", "—") if products else "—"
    answer = f"热销 TOP{len(products)}，冠军商品：{top}。"
    option = build_bar_option("热销商品 TOP", names, gmv, horizontal=True)
    return answer, {"type": "bar", "title": "热销商品", "option": option}, None


def from_template_status(data: dict) -> tuple[str, dict, dict | None]:
    statuses = data.get("statuses", [])
    pie_data = [{"name": s.get("status_name"), "value": s.get("order_count", 0)} for s in statuses]
    answer = "订单状态分布：" + "，".join(f"{s['status_name']} {s['order_count']}" for s in statuses[:5])
    option = build_pie_option("订单状态", pie_data)
    return answer, {"type": "pie", "title": "订单状态", "option": option}, None


def from_query_rows(
    rows: list[dict],
    chart_type: str,
    title: str,
) -> tuple[str, dict, dict | None]:
    if not rows:
        return "查询无结果，请调整日期或问法。", {"type": "none", "title": title, "option": None}, {"columns": [], "rows": []}

    table = rows_to_table(rows)
    keys = list(rows[0].keys())

    if chart_type == "line" and len(keys) >= 2:
        x_key = keys[0]
        y_keys = keys[1:]
        option = build_line_option(
            title,
            [str(r.get(x_key)) for r in rows],
            [{"name": k, "type": "line", "smooth": True, "data": [r.get(k) for r in rows]} for k in y_keys],
        )
        answer = f"共 {len(rows)} 条记录，已生成折线图。"
        return answer, {"type": "line", "title": title, "option": option}, table

    if chart_type == "bar" and len(keys) >= 2:
        cat_key, val_key = keys[0], keys[1]
        option = build_bar_option(
            title,
            [str(r.get(cat_key)) for r in rows],
            [r.get(val_key) for r in rows],
            horizontal=len(rows) <= 10,
        )
        return f"共 {len(rows)} 条，已生成柱状图。", {"type": "bar", "title": title, "option": option}, table

    if chart_type == "pie" and len(keys) >= 2:
        name_k, val_k = keys[0], keys[1]
        pie = [{"name": r.get(name_k), "value": r.get(val_k)} for r in rows]
        option = build_pie_option(title, pie)
        return f"共 {len(rows)} 项，已生成饼图。", {"type": "pie", "title": title, "option": option}, table

    if chart_type == "funnel":
        name_k, val_k = keys[0], keys[1] if len(keys) > 1 else keys[0]
        if len(keys) == 1:
            row = rows[0]
            stages = [{"name": k, "value": int(row.get(k) or 0)} for k in keys]
        else:
            stages = [{"name": str(r.get(name_k)), "value": int(r.get(val_k) or 0)} for r in rows]
        option = build_funnel_option(title, stages)
        return "漏斗数据已生成。", {"type": "funnel", "title": title, "option": option}, table

    summary = "；".join(f"{k}={rows[0].get(k)}" for k in keys[:4])
    return f"查询结果：{summary} 等共 {len(rows)} 行。", {"type": "table", "title": title, "option": None}, table
