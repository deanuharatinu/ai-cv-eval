import asyncio

from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable, Optional


class InProcessQueue:
    """Minimal background task runner for evaluation jobs."""

    def __init__(self, max_workers: int = 4) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="eval-worker")

    def submit(self, func: Callable[[], Awaitable[None]]) -> None:
        """Submit coroutine-producing callable to run in threadpool."""

        async def runner() -> None:
            await func()

        loop = self._ensure_loop()
        loop.create_task(runner())

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        loop = self._loop
        if loop and not loop.is_closed():
            return loop
        loop = asyncio.get_running_loop()
        self._loop = loop
        return loop
