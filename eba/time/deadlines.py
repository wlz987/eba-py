from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


ELAPSED = 0


class Deadlines(Generic[T]):
    def __init__(self) -> None:
        self._items: list[tuple[int, int, T]] = []
        self._positions: dict[T, int] = {}
        self._sequence = 0

    def at(self, item_id: T) -> int | None:
        index = self._positions.get(item_id)
        if index is None:
            return None
        return self._items[index][0]

    @property
    def next_ms(self) -> int | None:
        if not self._items:
            return None
        return self._items[0][0]

    def add(self, item_id: T, at: int) -> None:
        if item_id in self._positions:
            raise RuntimeError("duplicate deadline")
        self._sequence += 1
        self._positions[item_id] = len(self._items)
        self._items.append((at, self._sequence, item_id))
        self._up(len(self._items) - 1)

    def remove(self, item_id: T) -> None:
        index = self._positions.pop(item_id, None)
        if index is None:
            return
        last = self._items.pop()
        if index == len(self._items):
            return
        self._items[index] = last
        self._positions[last[2]] = index
        self._up(index)
        self._down(index)

    def peek_due(self, now_ms: int) -> T | None:
        if not self._items or self._items[0][0] > now_ms:
            return None
        return self._items[0][2]

    def _before(self, left: tuple[int, int, T], right: tuple[int, int, T]) -> bool:
        return left[0] < right[0] or (left[0] == right[0] and left[1] < right[1])

    def _swap(self, left: int, right: int) -> None:
        a: tuple[int, int, T] = self._items[left]
        b: tuple[int, int, T] = self._items[right]
        self._items[left] = b
        self._items[right] = a
        self._positions[a[2]] = right
        self._positions[b[2]] = left

    def _up(self, index: int) -> None:
        while index > 0:
            parent = (index - 1) // 2
            if not self._before(self._items[index], self._items[parent]):
                return
            self._swap(index, parent)
            index = parent

    def _down(self, index: int) -> None:
        length = len(self._items)
        while 2 * index + 1 < length:
            child = 2 * index + 1
            if child + 1 < length and self._before(self._items[child + 1], self._items[child]):
                child += 1
            if not self._before(self._items[child], self._items[index]):
                return
            self._swap(index, child)
            index = child
