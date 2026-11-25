"""Gemini provider via langchain-google-genai."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.core.logging import logger
from app.services.llm.base import BaseLLMProvider, LLMDecision, LLMMessage, LLMProviderError, ToolCallRequest


class GeminiProvider(BaseLLMProvider):
    name = "gemini"

    def __init__(self, settings: Optional[Settings] = None, llm=None):
        self.settings = settings or get_settings()
        self._llm = llm

    def is_configured(self) -> bool:
        return bool(self.settings.gemini_api_key)

    def _get_llm(self, tools: List[Dict[str, Any]]):
        if self._llm is not None:
            return self._llm
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.tools import StructuredTool
        from pydantic import create_model

        llm = ChatGoogleGenerativeAI(
            model=self.settings.gemini_model,
            google_api_key=self.settings.gemini_api_key,
            temperature=0.1,
            timeout=self.settings.llm_timeout_seconds,
        )
        bound_tools = []
        for tool in tools:
            props = (tool.get("parameters") or {}).get("properties") or {}
            fields = {key: (Any, ...) for key in props.keys()} or {"_noop": (Optional[str], None)}
            args_model = create_model(f"{tool['name']}Args", **fields)

            def _fn(**kwargs):  # pragma: no cover - bound only for schema
                return kwargs

            bound_tools.append(
                StructuredTool.from_function(
                    func=_fn,
                    name=tool["name"],
                    description=tool.get("description") or tool["name"],
                    args_schema=args_model,
                )
            )
        return llm.bind_tools(bound_tools) if bound_tools else llm

    def decide(self, messages: List[LLMMessage], tools: List[Dict[str, Any]], *, temperature: float = 0.1) -> LLMDecision:
        if not self.is_configured():
            raise LLMProviderError("Gemini is not configured", retryable=False, provider=self.name)
        try:
            llm = self._get_llm(tools)
            lc_messages = [{"role": m.role, "content": m.content} for m in messages]
            response = llm.invoke(lc_messages)
            tool_calls: List[ToolCallRequest] = []
            for call in getattr(response, "tool_calls", None) or []:
                args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
                name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
                call_id = call.get("id") if isinstance(call, dict) else getattr(call, "id", None)
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                tool_calls.append(ToolCallRequest(name=name, arguments=args or {}, id=call_id))
            content = response.content if isinstance(response.content, str) else str(response.content or "")
            return LLMDecision(
                content=content or None,
                tool_calls=tool_calls,
                provider=self.name,
                model=self.settings.gemini_model,
            )
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            retryable = any(t in message.lower() for t in ("rate", "timeout", "temporar", "unavailable", "429", "503", "500"))
            logger.warning("Gemini decide failed: %s", message)
            raise LLMProviderError(message, retryable=retryable, provider=self.name) from exc
