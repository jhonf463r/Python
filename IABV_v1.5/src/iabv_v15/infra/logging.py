from __future__ import annotations

from pathlib import Path
import logging

# Loggers whose per-request INFO lines are pure noise for IABV.
# The important information (tool availability, disagreements,
# auto-corrections) is logged at the IABV service level; individual
# HTTP request/response lines add no diagnostic value and pollute the
# log, making it harder to find real findings.
_NOISY_HTTP_LOGGERS: tuple[str, ...] = (
    'httpx',
    'httpcore',
    'httpcore.http11',
    'httpcore.connection',
    'urllib3',
    'urllib3.connectionpool',
)


def suppress_noisy_http_loggers() -> None:
    """Set noisy HTTP transport loggers to WARNING.

    Safe to call multiple times and at any point in the process lifetime.
    Call this as early as possible (before heavy imports) so that httpx
    noise never reaches the log in the first place.
    """
    for name in _NOISY_HTTP_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def configure_logging(logs_dir: str) -> None:
    path = Path(logs_dir)
    path.mkdir(parents=True, exist_ok=True)

    # Always suppress HTTP noise, even if handlers were already set up
    # by another path (e.g. basicConfig auto-config, MCP subprocess).
    suppress_noisy_http_loggers()

    logger = logging.getLogger()
    if logger.handlers:
        return

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(path / "iabv_v15.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
