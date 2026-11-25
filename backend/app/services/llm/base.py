"""Common LLM provider interface with tool-calling support."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class ToolCallRequest:
    name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None


@dataclass
class LLMDecision:
    content: Optional[str]
    tool_calls: List[ToolCallRequest] = field(default_factory=list)
    provider: str = "unknown"
    model: str = "unknown"
    raw: Dict[str, Any] = field(default_factory=dict)


class LLMProviderError(Exception):
    def __init__(self, message: str, *, retryable: bool = False, provider: str = "unknown"):
        super().__init__(message)
        self.retryable = retryable
        self.provider = provider


class BaseLLMProvider(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def decide(
        self,
        messages: List[LLMMessage],
        tools: List[Dict[str, Any]],
        *,
        temperature: float = 0.1,
    ) -> LLMDecision:
        ...
