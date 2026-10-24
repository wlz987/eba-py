from __future__ import annotations

from collections import deque
from typing import Generic, TypeVar

from eba.job.reply import Reply

K = TypeVar("K")
V = TypeVar("V")

_CREDIT_LIMIT = 4096  # 每个键的唤醒信用上限；满了丢新的


class _Waiter(Generic[V]):
    __slots__ = ("deadline", "owner", "reply")

    def __init__(self, reply: Reply, deadline: int | None, owner: object | None) -> None:
        self.reply = reply
        self.deadline = deadline
        self.owner = owner


def _pop(queue: deque[_Waiter[V]]) -> _Waiter[V] | None:
    while queue:
        waiter = queue.popleft()
        if not waiter.reply.is_closed:
            return waiter
    return None


class Park(Generic[K, V]):
    """Keyed waits: many Replies per key, one wake consumed by one live waiter.

    Keys are hashable and deadlines are absolute milliseconds. A wake that finds
    nobody is kept as a credit for the next waiter; a key keeps at most 4096
    credits, extra wakes are dropped. Wakes, expiries and cancellations return
    live Replies for the caller to settle; a consumed credit leaves its Reply to
    the caller. Requeues move between distinct keys; expiry scans the waiters.
    An owner scopes cancellation: cancel_owner removes only its waiters, never
    another owner's wait on the same key; credits stay key-scoped.
    """

    def __init__(self) -> None:
        self._waiters: dict[K, deque[_Waiter[V]]] = {}
        self._credits: dict[K, deque[V]] = {}

    def wait(
        self,
        key: K,
        reply: Reply,
        deadline_ms: int | None = None,
        owner: object | None = None,
    ) -> V | None:
        credits = self._credits.get(key)
        if credits:
            value = credits.popleft()
            if not credits:
                del self._credits[key]
            return value
        queue = self._waiters.get(key)
        if queue is None:
            self._waiters[key] = deque([_Waiter(reply, deadline_ms, owner)])
        else:
            queue.append(_Waiter(reply, deadline_ms, owner))
        return None

    def wake(self, key: K, value: V) -> Reply | None:
        queue = self._waiters.get(key)
        waiter = None if queue is None else _pop(queue)
        self._drop(key)
        if waiter is not None:
            return waiter.reply
        credits = self._credits.get(key)
        if credits is None:
            credits = deque()
            self._credits[key] = credits
        if len(credits) < _CREDIT_LIMIT:
            credits.append(value)
        return None

    def take(self, key: K, count: int) -> list[Reply]:
        if count <= 0:
            return []
        taken: list[Reply] = []
        queue = self._waiters.get(key)
        while queue and len(taken) < count:
            waiter = _pop(queue)
            if waiter is None:
                break
            taken.append(waiter.reply)
        self._drop(key)
        return taken

    def move_waiters(self, from_key: K, to_key: K, count: int) -> int:
        if from_key == to_key or count <= 0:
            return 0
        source = self._waiters.get(from_key)
        if not source:
            return 0
        target = self._waiters.setdefault(to_key, deque())
        moved = 0
        while moved < count:
            waiter = _pop(source)
            if waiter is None:
                break
            target.append(waiter)
            moved += 1
        if not source:
            del self._waiters[from_key]
        if not target:
            del self._waiters[to_key]
        return moved

    def requeue(self, from_key: K, to_key: K, wake: int, requeue: int) -> list[Reply]:
        woken = self.take(from_key, wake)
        self.move_waiters(from_key, to_key, requeue)
        return woken

    def expire(self, now_ms: int) -> list[Reply]:
        expired: list[Reply] = []
        for key in list(self._waiters):
            queue = self._waiters[key]
            kept: deque[_Waiter[V]] = deque()
            for waiter in queue:
                if waiter.deadline is not None and waiter.deadline <= now_ms:
                    if not waiter.reply.is_closed:
                        expired.append(waiter.reply)
                else:
                    kept.append(waiter)
            if kept:
                self._waiters[key] = kept
            else:
                del self._waiters[key]
        return expired

    def cancel(self, key: K) -> list[Reply]:
        self._credits.pop(key, None)
        queue = self._waiters.pop(key, None)
        if queue is None:
            return []
        return [waiter.reply for waiter in queue if not waiter.reply.is_closed]

    def cancel_owner(self, owner: object) -> list[Reply]:
        cancelled: list[Reply] = []
        for key in list(self._waiters):
            queue = self._waiters[key]
            kept: deque[_Waiter[V]] = deque()
            for waiter in queue:
                if waiter.owner == owner:
                    if not waiter.reply.is_closed:
                        cancelled.append(waiter.reply)
                else:
                    kept.append(waiter)
            if kept:
                self._waiters[key] = kept
            else:
                del self._waiters[key]
        return cancelled

    def keys(self) -> list[K]:
        return list(self._waiters)

    def _drop(self, key: K) -> None:
        queue = self._waiters.get(key)
        if queue is not None and not queue:
            del self._waiters[key]
