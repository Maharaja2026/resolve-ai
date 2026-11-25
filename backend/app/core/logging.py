"""Safe logging helpers that never emit secrets."""

from __future__ import annotations

import logging
import re

SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key\s*[:=]\s*)([^\s,]+)", re.IGNORECASE),
    re.compile(r"(authorization\s*[:=]\s*bearer\s+)([^\s,]+)", re.IGNORECASE),
    re.compile(r"(service[_-]?role[_-]?key\s*[:=]\s*)([^\s,]+)", re.IGNORECASE),
]


def setup_logging(debug: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted


logger = logging.getLogger("resolveai")
