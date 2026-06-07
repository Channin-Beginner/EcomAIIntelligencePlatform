from typing import Any, Literal

from pydantic import BaseModel, Field


class AssistantQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    refDate: str | None = Field(None, description="参考日期 YYYY-MM-DD")
    sessionId: str | None = None


class ChartPayload(BaseModel):
    type: Literal["line", "bar", "pie", "funnel", "table", "none"] = "none"
    title: str = ""
    option: dict[str, Any] | None = None


class TablePayload(BaseModel):
    columns: list[str] = []
    rows: list[list[Any]] = []


class AssistantQueryResponse(BaseModel):
    answer: str
    route: Literal["template", "nl2sql", "fallback"]
    refDate: str
    sql: str | None = None
    chart: ChartPayload
    table: TablePayload | None = None
