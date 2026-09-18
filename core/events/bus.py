"""
Antigravity QuantEngine - Asynchronous Event Bus
Provides decoupled, non-blocking pub/sub message dispatch with error isolation.
"""

import asyncio
from typing import Callable, Dict, List, Type, Awaitable
from core.events.events import BaseEvent
from core.logging import get_logger

logger = get_logger("events.bus")

EventHandler = Callable[[BaseEvent], Awaitable[None]]


class EventBus:
    """Central decoupled in-memory async event dispatcher."""

    def __init__(self, max_queue_size: int = 20000):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._worker_task: asyncio.Task | None = None
        self._running = False

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        self._wildcard_handlers.append(handler)

    async def publish(self, event: BaseEvent) -> None:
        """Publish event directly to subscribers asynchronously without blocking caller."""
        handlers = list(self._handlers.get(event.event_type, [])) + self._wildcard_handlers
        for handler in handlers:
            try:
                # Run handler as a background task to prevent slow subscribers from blocking
                asyncio.create_task(self._safe_invoke(handler, event))
            except Exception as e:
                logger.error(f"Failed to dispatch event {event.event_type}: {e}", exc_info=True)

    async def _safe_invoke(self, handler: EventHandler, event: BaseEvent) -> None:
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Error in event handler {handler.__name__} for {event.event_type}: {e}",
                exc_info=True
            )


# Global event bus
_EVENT_BUS: EventBus | None = None


def get_event_bus() -> EventBus:
    global _EVENT_BUS
    if _EVENT_BUS is None:
        _EVENT_BUS = EventBus()
    return _EVENT_BUS
