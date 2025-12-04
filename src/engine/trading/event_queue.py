# src/engine/trading/event_queue.py

from collections import deque
from typing import Optional, Any


class EventQueue:
    """
    TradingEngine이 사용할 내부 시그널/이벤트 큐
    매우 단순한 FIFO 큐
    """

    def __init__(self):
        self._queue = deque()

    def push(self, item: Any):
        self._queue.append(item)

    def pop(self) -> Optional[Any]:
        if self._queue:
            return self._queue.popleft()
        return None

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def size(self) -> int:
        return len(self._queue)
