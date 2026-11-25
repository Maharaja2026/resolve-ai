"""Groq provider via langchain-groq with free-tier model fallbacks."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence

from app.core.config import Settings, get_settings
from app.core.logging import logger
from app.services.llm.base import BaseLLMProvider, LLMDecision, LLMMessage, LLMProviderError, ToolCallRequest

GROQ_MODEL_FALLBACKS: Sequence[str] = (
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
)


class GroqProvider(BaseLLMProvider):
    name = "groq"

    def __init__(self, settings: Optional[Settings] = None, llm=None):
        self.settings = settings or get_settings()
        self._llm = llm
        self._resolved_model: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.settings.groq_api_key)

    def _candidate_models(self) -> List[str]:
        preferred = self._resolved_model or self.settings.groq_model
        models = []
        for model in (preferred, *GROQ_MODEL_FALLBACKS):
            if model and model not in models:
                models.append(model)
        return models

    def _build_llm(self, model: str, tools: List[Dict[str, Any]]):
        from langchain_groq import ChatGroq
        from langchain_core.tools import StructuredTool
        from pydantic import create_model

        llm = ChatGroq(
            model=model,
            api_key=self.settings.groq_api_key,
            temperature=0.1,
            timeout=self.settings.llm_timeout_seconds,
        )
        bound_tools = []
        for tool in tools:
            props = (tool.get("parameters") or {}).get("properties") or {}
            fields = {key: (Any, ...) for key in props.keys()} or {"_noop": (Optional[str], None)}
            args_model = create_model(f"{tool['name']}Args", **fields)

            def _fn(**kwargs):  # pragma: no cover
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
            raise LLMProviderError("Groq is not configured", retryable=False, provider=self.name)

        errors = []
        lc_messages = [{"role": m.role, "content": m.content} for m in messages]
        for model in self._candidate_models():
            try:
                llm = self._llm or self._build_llm(model, tools)
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
                self._resolved_model = model
                return LLMDecision(
                    content=content or None,
                    tool_calls=tool_calls,
                    provider=self.name,
                    model=model,
                )
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                errors.append(f"{model}: {message}")
                logger.warning("Groq model %s failed: %s", model, message)
                if any(t in message.lower() for t in ("model_not_found", "does not exist", "do not have access")):
                    continue
                retryable = any(t in message.lower() for t in ("rate", "timeout", "temporar", "unavailable", "429", "503"))
                raise LLMProviderError(message, retryable=retryable, provider=self.name) from exc

        raise LLMProviderError("Groq models unavailable: " + " | ".join(errors), retryable=False, provider=self.name)
