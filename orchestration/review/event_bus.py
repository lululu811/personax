# orchestration/review/event_bus.py
from typing import Callable, Any
import threading


class EventBus:
    """轻量事件总线，支持 Fire & Forget"""

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()

    def emit(self, event_type: str, data: Any):
        """非阻塞发射事件"""
        with self._lock:
            handlers = list(self._handlers.get(event_type, []))

        for handler in handlers:
            threading.Thread(target=handler, args=(data,), daemon=True).start()

    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件"""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""
        with self._lock:
            if event_type in self._handlers:
                try:
                    self._handlers[event_type].remove(handler)
                except ValueError:
                    pass


_global_bus = EventBus()


def emit(event_type: str, data: Any):
    """全局发射事件"""
    _global_bus.emit(event_type, data)


def subscribe(event_type: str, handler: Callable):
    """全局订阅事件"""
    _global_bus.subscribe(event_type, handler)