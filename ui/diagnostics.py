"""Lightweight diagnostic breadcrumbs for desktop stability UAT.

Logs contain lifecycle information and operation status, not Journey contents.
The native rotating log survives console loss and Flet session replacement.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
import threading
from datetime import datetime
from pathlib import Path
from ui.storage.file_storage_backend import default_storage_dir

_logger = logging.getLogger("pokemon_battle_compass.diagnostics")
_logger.setLevel(logging.INFO)
_logger.propagate = False
_lock = threading.Lock()
_native_ready = False
_session_counter = 0
_active_token = 0
_active_closed = True


def configure_native_logging() -> Path:
    """Enable rotating, persistent diagnostics once per native Python process."""
    global _native_ready
    path = default_storage_dir().parent / "logs" / "desktop.log"
    with _lock:
        if not _native_ready:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                handler = RotatingFileHandler(
                    path, maxBytes=2_000_000, backupCount=4, encoding="utf-8"
                )
                handler.setFormatter(logging.Formatter("%(message)s"))
                _logger.addHandler(handler)
                _native_ready = True
            except OSError as error:
                # Never prevent application startup because logging is unavailable.
                print(f"DIAG file logging unavailable: {error}", flush=True)
    return path


def log_event(category: str, message: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    record = f"[{stamp}] pid={os.getpid()} {category} {message}"
    print(record, flush=True)
    if _native_ready:
        _logger.info(record)


def begin_session(page_id: int, session_id: int) -> int:
    """Track session replacement within the same Python process."""
    global _session_counter, _active_token, _active_closed
    with _lock:
        previous = _active_token
        previous_closed = _active_closed
        _session_counter += 1
        token = _session_counter
        _active_token = token
        _active_closed = False
    if previous:
        log_event(
            "SESSION",
            f"new session #{token}; previous #{previous} "
            f"close_event_observed={previous_closed}",
        )
    log_event("SESSION", f"begin token={token} page_id={page_id} session_id={session_id}")
    return token


def mark_session_closed(token: int) -> None:
    global _active_closed
    with _lock:
        if token == _active_token:
            _active_closed = True


def session_is_current(token: int) -> bool:
    with _lock:
        return token == _active_token and not _active_closed
