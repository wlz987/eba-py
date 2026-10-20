from collections import deque
from collections.abc import Iterator

from eba.time.numbers import positive_int


class Queue:
    def __init__(self, capacity: int) -> None:
        self.capacity = positive_int(capacity, "capacity")
        self._items: deque[object] = deque()

    @property
    def size(self) -> int:
        return len(self._items)

    @property
    def full(self) -> bool:
        return len(self._items) >= self.capacity

    def push(self, item: object) -> bool:
        if self.full:
            return False
        self._items.append(item)
        return True

    def __iter__(self) -> Iterator[object]:
        return iter(self._items)

    def shift(self) -> object | None:
        if not self._items:
            return None
        return self._items.popleft()
