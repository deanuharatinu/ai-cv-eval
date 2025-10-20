from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Awaitable, Callable, Iterable, Optional, TypeVar

from google.genai import errors

T = TypeVar("T")


def _default_logger() -> logging.Logger:
    return logging.getLogger(__name__)


def _compute_sleep(
    attempt: int, *, base_delay: float, max_delay: float, jitter: float
) -> float:
    backoff = min(max_delay, base_delay * (2 ** (attempt - 1)))
    if jitter <= 0:
        return backoff
    return backoff + random.uniform(0, jitter)


def _should_retry_default(
    exc: BaseException, *, retry_exceptions: Iterable[type[BaseException]] | None
) -> bool:
    if retry_exceptions is None:
        return True
    return any(isinstance(exc, candidate) for candidate in retry_exceptions)


async def async_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    jitter: float = 0.25,
    retry_exceptions: Iterable[type[BaseException]] | None = None,
    should_retry: Optional[Callable[[BaseException], bool]] = None,
    logger: Optional[logging.Logger] = None,
    context: str = "operation",
) -> T:
    """Retry an async operation with exponential backoff and optional jitter."""

    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    log = logger or _default_logger()
    last_exc: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except Exception as exc:
            retry_allowed = (
                should_retry(exc)
                if should_retry
                else _should_retry_default(exc, retry_exceptions=retry_exceptions)
            )
            if not retry_allowed or attempt == attempts:
                last_exc = exc
                break

            sleep_for = _compute_sleep(
                attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter=jitter,
            )
            log.warning(
                "Retryable error during %s (attempt %s/%s): %s; retrying in %.2fs",
                context,
                attempt,
                attempts,
                exc,
                sleep_for,
            )
            await asyncio.sleep(sleep_for)

    assert last_exc is not None
    raise last_exc


def sync_retry(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    jitter: float = 0.25,
    retry_exceptions: Iterable[type[BaseException]] | None = None,
    should_retry: Optional[Callable[[BaseException], bool]] = None,
    logger: Optional[logging.Logger] = None,
    context: str = "operation",
) -> T:
    """Retry a sync operation with exponential backoff and optional jitter."""

    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    log = logger or _default_logger()
    last_exc: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            retry_allowed = (
                should_retry(exc)
                if should_retry
                else _should_retry_default(exc, retry_exceptions=retry_exceptions)
            )
            if not retry_allowed or attempt == attempts:
                last_exc = exc
                break

            sleep_for = _compute_sleep(
                attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter=jitter,
            )
            log.warning(
                "Retryable error during %s (attempt %s/%s): %s; retrying in %.2fs",
                context,
                attempt,
                attempts,
                exc,
                sleep_for,
            )
            time.sleep(sleep_for)

    assert last_exc is not None
    raise last_exc


def is_retryable_gemini_error(exc: BaseException) -> bool:
    """Best-effort detection of transient Gemini API failures."""

    if isinstance(exc, errors.APIError):
        return True

    return False
