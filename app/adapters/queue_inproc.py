import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable


class InProcessQueue:
    """Minimal background task runner for evaluation jobs."""

    def __init__(self, max_workers: int = 4) -> None:
        self._loop = asyncio.get_event_loop()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="eval-worker")

    def submit(self, func: Callable[[], Awaitable[None]]) -> None:
        """Submit coroutine-producing callable to run in threadpool."""

        async def runner() -> None:
            await func()

        self._loop.create_task(runner())
