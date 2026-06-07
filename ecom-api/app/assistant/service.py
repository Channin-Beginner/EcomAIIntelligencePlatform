from __future__ import annotations

from sqlalchemy.orm import Session

from app.admin import ops_service
from app.assistant.llm_client import DoubaoClient, LlmClientError, get_llm_client
from app.assistant.nl2sql import run_nl2sql
from app.assistant.schema import AssistantQueryResponse, ChartPayload, TablePayload
from app.assistant.template_router import match_template, run_template

SUGGESTIONS = [
    "今日 GMV 和订单数是多少？",
    "展示近 30 天 GMV 趋势",
    "转化漏斗各阶段人数",
    "当日 UV 和 PV 是多少？",
    "地域销售 TOP5 省份",
    "热销商品 TOP10",
    "6 月 15 日 24 小时销售曲线",
    "订单状态分布",
]


def get_suggestions() -> list[str]:
    return SUGGESTIONS


def handle_query(db: Session, question: str, ref_date: str | None) -> AssistantQueryResponse:
    ref = ops_service.parse_ref_date(db, ref_date)
    ref_str = ref.isoformat()
    q = question.strip()

    kind = match_template(q)
    tpl = run_template(db, kind, ref_str)
    if tpl:
        answer, chart, table, _tag = tpl
        return AssistantQueryResponse(
            answer=answer,
            route="template",
            refDate=ref_str,
            sql=None,
            chart=ChartPayload(**chart),
            table=TablePayload(**table) if table else None,
        )

    client: DoubaoClient = get_llm_client()
    if not client.configured:
        return AssistantQueryResponse(
            answer=(
                "未配置豆包 API，已尝试模板路由但未命中。"
                "请在 ecom-api/.env 设置 LLM_API_KEY 与 LLM_MODEL（火山方舟推理接入点 ID）。"
                "也可试试推荐问题。"
            ),
            route="fallback",
            refDate=ref_str,
            chart=ChartPayload(type="none", title=""),
            table=None,
        )

    try:
        answer, chart, table, sql = run_nl2sql(db, client, q, ref_str)
        return AssistantQueryResponse(
            answer=answer,
            route="nl2sql",
            refDate=ref_str,
            sql=sql,
            chart=ChartPayload(**chart),
            table=TablePayload(**table) if table else None,
        )
    except LlmClientError as exc:
        return AssistantQueryResponse(
            answer=f"智能分析暂时失败：{exc}。建议使用下方推荐问题，或检查豆包 API 配置。",
            route="fallback",
            refDate=ref_str,
            chart=ChartPayload(type="none", title=""),
            table=None,
        )
