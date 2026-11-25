"""LangGraph checkpointer factory (SQLite by default for free-tier isolation)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

from app.core.config import get_settings
from app.core.logging import logger

# Keep the SQLite connection alive for the process lifetime.
_SQLITE_CONN: Optional[sqlite3.Connection] = None
_CHECKPOINTER: Any = None


def build_checkpointer():
    """Return a real BaseCheckpointSaver (not a context manager)."""
    global _SQLITE_CONN, _CHECKPOINTER
    if _CHECKPOINTER is not None:
        return _CHECKPOINTER

    settings = get_settings()
    if settings.checkpointer_backend == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        _CHECKPOINTER = MemorySaver()
        return _CHECKPOINTER

    path = Path(settings.checkpoint_database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        # from_conn_string() yields a context manager — do not return that directly.
        _SQLITE_CONN = sqlite3.connect(str(path), check_same_thread=False)
        saver = SqliteSaver(_SQLITE_CONN)
        saver.setup()
        logger.info("Using SQLite LangGraph checkpointer at %s", path)
        _CHECKPOINTER = saver
        return _CHECKPOINTER
    except Exception as exc:  # noqa: BLE001
        logger.warning("SQLite checkpointer unavailable (%s); falling back to MemorySaver", exc)
        from langgraph.checkpoint.memory import MemorySaver

        _CHECKPOINTER = MemorySaver()
        return _CHECKPOINTER
