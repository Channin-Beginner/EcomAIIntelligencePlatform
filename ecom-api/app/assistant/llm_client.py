from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class LlmClientError(Exception):
    pass


class DoubaoClient:
    """火山引擎豆包 — OpenAI 兼容 Chat Completions。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_base = settings.llm_api_base.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        if not self.configured:
            raise LlmClientError("未配置豆包 API：请在 ecom-api/.env 设置 LLM_API_KEY 与 LLM_MODEL")

        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.exception("Doubao API request failed")
            raise LlmClientError(f"豆包 API 调用失败: {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmClientError(f"豆包响应格式异常: {data}") from exc

    def chat_json(self, messages: list[dict[str, str]], temperature: float = 0.1) -> dict[str, Any]:
        content = self.chat(messages, temperature=temperature)
        text = content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LlmClientError(f"豆包未返回合法 JSON: {content[:200]}") from exc


def get_llm_client() -> DoubaoClient:
    return DoubaoClient()
