"""Event bus subsystem for asynchronous run progress and status events."""

import asyncio
import logging
from typing import Dict, Set, Callable, Awaitable, Any, Union

logger = logging.getLogger("event_bus")

EventHandler = Union[Callable[[dict], None], Callable[[dict], Awaitable[None]]]

class EventBus:
    """
    In-memory asynchronous event bus supporting multi-subscriber decoupled channels.
    Serves as the foundation for WebSocket streaming and extension hook for Redis PubSub.
    """
    def __init__(self):
        self._listeners: Dict[str, Set[EventHandler]] = {}
        self._lock = asyncio.Lock()

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Register a synchronous or asynchronous event listener for a topic."""
        if topic not in self._listeners:
            self._listeners[topic] = set()
        self._listeners[topic].add(handler)

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """Remove an event listener from a topic."""
        if topic in self._listeners:
            self._listeners[topic].discard(handler)
            if not self._listeners[topic]:
                self._listeners.pop(topic, None)

    async def publish(self, topic: str, event_data: dict) -> None:
        """Broadcast an event payload to all topic subscribers safely."""
        subscribers = list(self._listeners.get(topic, set()))
        for handler in subscribers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as exc:
                logger.debug("Error delivering event to listener on topic %s: %s", topic, exc)

# Global singleton event bus
event_bus = EventBus()
