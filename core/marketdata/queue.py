"""
Antigravity QuantEngine - Bounded Queue & Conservation Accounting
Enforces strict backpressure, fail-closed queue safety, and the conservation invariant:
received == persisted + rejected + explicitly_lost + unknown
"""

import asyncio
from typing import Any, Dict, Optional
from pydantic import BaseModel
from core.logging import get_logger

logger = get_logger("marketdata.queue")


class QueueConservationStats(BaseModel):
    received: int = 0
    persisted: int = 0
    rejected: int = 0
    explicitly_lost: int = 0
    unknown: int = 0

    @property
    def is_conserved(self) -> bool:
        return self.received == (
            self.persisted + self.rejected + self.explicitly_lost + self.unknown
        )

    @property
    def discrepancy(self) -> int:
        return self.received - (
            self.persisted + self.rejected + self.explicitly_lost + self.unknown
        )


class BoundedMarketDataQueue:
    """Async bounded queue with backpressure and mathematical conservation enforcement."""

    def __init__(self, maxsize: int = 50000):
        self.maxsize = maxsize
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.stats = QueueConservationStats()

    async def put(self, item: Any, timeout: Optional[float] = 2.0) -> bool:
        """
        Put item onto queue with timeout.
        If queue is completely saturated and timeout elapses: FAIL CLOSED.
        Record explicitly as lost/rejected, never drop silently.
        """
        self.stats.received += 1
        try:
            if timeout is None or timeout <= 0:
                self._queue.put_nowait(item)
            else:
                await asyncio.wait_for(self._queue.put(item), timeout=timeout)
            return True
        except (asyncio.QueueFull, asyncio.TimeoutError):
            self.stats.explicitly_lost += 1
            logger.error(
                f"BACKPRESSURE OVERFLOW: Queue capacity ({self.maxsize}) reached! "
                f"Fail-closed: explicitly rejected wire message."
            )
            return False

    async def get(self) -> Any:
        return await self._queue.get()

    def record_persisted(self, count: int = 1) -> None:
        self.stats.persisted += count

    def record_rejected(self, count: int = 1) -> None:
        self.stats.rejected += count

    def record_unknown(self, count: int = 1) -> None:
        self.stats.unknown += count

    @property
    def qsize(self) -> int:
        return self._queue.qsize()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "qsize": self._queue.qsize(),
            "maxsize": self.maxsize,
            "utilization_pct": round((self._queue.qsize() / max(1, self.maxsize)) * 100, 2),
            "stats": self.stats.model_dump(),
            "is_conserved": self.stats.is_conserved,
            "discrepancy": self.stats.discrepancy
        }
