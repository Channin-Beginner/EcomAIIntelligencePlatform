from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.assistant.chart_builder import from_query_rows
from app.assistant.llm_client import DoubaoClient, LlmClientError
from app.assistant.sql_guard import validate_sql
from app.database import fetch_all

_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_FILE = _ROOT / "docs" / "mall_schema_for_llm.json"
_EXAMPLES_FILE = _ROOT / "docs" / "nl2sql_examples.jsonl"
_METRICS_FILE = _ROOT / "docs" / "metrics_dictionary.md"


def _load_schema_text() -> str:
    if _SCHEMA_FILE.exists():
        return _SCHEMA_FILE.read_text(encoding="utf-8")
    return "{}"


def _load_examples(max_n: int = 5) -> str:
    if not _EXAMPLES_FILE.exists():
        return ""
    lines = _EXAMPLES_FILE.read_text(encoding="utf-8").strip().splitlines()[:max_n]
    return "\n".join(lines)


def _load_metrics_summary() -> str:
    if not _METRICS_FILE.exists():
        return ""
    text = _METRICS_FILE.read_text(encoding="utf-8")
    return text[:2500]


def generate_sql(client: DoubaoClient, question: str, ref_date: str) -> dict:
    system = (
        "你是电商数据分析 SQL 专家。根据用户问题生成 MySQL SELECT 语句。"
        "只能使用白名单表，必须带 LIMIT（≤500）。"
        "输出严格 JSON，不要 markdown："
        '{"sql":"...", "chartType":"line|bar|pie|funnel|table", "title":"图表标题"}'
    )
    user = (
        f"参考日期 refDate={ref_date}。使用数据库全量业务数据，不要人为限制时间窗口。\n\n"
        f"## Schema 白名单\n{_load_schema_text()}\n\n"
        f"## 指标字典摘要\n{_load_metrics_summary()}\n\n"
        f"## Few-shot 示例\n{_load_examples()}\n\n"
        f"用户问题：{question}"
    )
    return client.chat_json(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )


def interpret_answer(client: DoubaoClient, question: str, rows: list[dict], ref_date: str) -> str:
    if not rows:
        return f"在参考日期 {ref_date} 未查到相关数据，可尝试切换日期或换个问法。"
    preview = json.dumps(rows[:5], ensure_ascii=False, default=str)
    messages = [
        {
            "role": "system",
            "content": "你是电商运营分析师。根据查询结果用 2~4 句中文给出结论，数字要具体，不要编造未给出的字段。",
        },
        {
            "role": "user",
            "content": f"问题：{question}\n参考日期：{ref_date}\n结果样例：{preview}\n总行数：{len(rows)}",
        },
    ]
    try:
        return client.chat(messages, temperature=0.3)
    except LlmClientError:
        return f"共查询到 {len(rows)} 条记录，详见下方图表与表格。"


def run_nl2sql(
    db: Session,
    client: DoubaoClient,
    question: str,
    ref_date: str,
) -> tuple[str, dict, dict | None, str]:
    spec = generate_sql(client, question, ref_date)
    sql = str(spec.get("sql", "")).strip()
    chart_type = str(spec.get("chartType", "table")).lower()
    title = str(spec.get("title", "查询结果"))

    safe_sql, errors = validate_sql(sql)
    if errors:
        raise LlmClientError("SQL 安全校验未通过: " + "; ".join(errors))

    rows = fetch_all(db, safe_sql)
    answer = interpret_answer(client, question, rows, ref_date)
    chart_answer, chart, table = from_query_rows(rows, chart_type, title)
    if len(answer) < 20:
        answer = chart_answer
    return answer, chart, table, safe_sql
