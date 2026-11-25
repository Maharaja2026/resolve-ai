"""Primary Gemini with Groq fallback for agent decisions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.core.logging import logger
from app.services.llm.base import BaseLLMProvider, LLMDecision, LLMMessage, LLMProviderError
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.groq_provider import GroqProvider


class LLMOrchestrator:
    def __init__(self, settings: Optional[Settings] = None, providers: Optional[Dict[str, BaseLLMProvider]] = None):
        self.settings = settings or get_settings()
        self.providers = providers or {
            "gemini": GeminiProvider(self.settings),
            "groq": GroqProvider(self.settings),
        }

    def status(self) -> Dict[str, Any]:
        return {
            name: {
                "configured": provider.is_configured(),
                "model": self.settings.gemini_model if name == "gemini" else self.settings.groq_model,
            }
            for name, provider in self.providers.items()
        }

    def decide(self, messages: List[LLMMessage], tools: List[Dict[str, Any]], *, temperature: float = 0.1) -> LLMDecision:
        ordered = []
        for name in (self.settings.llm_primary_provider, self.settings.llm_fallback_provider):
            provider = self.providers.get(name.lower())
            if provider and provider not in ordered:
                ordered.append(provider)
        errors = []
        for index, provider in enumerate(ordered):
            if not provider.is_configured():
                errors.append(f"{provider.name}: not configured")
                continue
            try:
                logger.info("Agent decision via provider=%s", provider.name)
                decision = provider.decide(messages, tools, temperature=temperature)
                if index > 0:
                    logger.info("Fell back to provider=%s model=%s", decision.provider, decision.model)
                return decision
            except LLMProviderError as exc:
                errors.append(f"{provider.name}: {exc}")
                logger.warning("Provider %s failed; trying next if available", provider.name)
                continue
        raise LLMProviderError("All LLM providers failed: " + " | ".join(errors), retryable=False, provider="orchestrator")


_orchestrator: Optional[LLMOrchestrator] = None


def get_llm_orchestrator(settings: Optional[Settings] = None) -> LLMOrchestrator:
    global _orchestrator
    if settings is not None:
        _orchestrator = LLMOrchestrator(settings=settings)
        return _orchestrator
    if _orchestrator is None:
        _orchestrator = LLMOrchestrator()
    return _orchestrator
