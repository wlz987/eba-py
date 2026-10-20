from __future__ import annotations

import weakref
from collections.abc import Callable

from eba.notify.signal import TIMER, Signal
from eba.time.deadlines import Deadlines
from eba.time.schedule import Schedule


class Agenda:
    def __init__(self) -> None:
        self.signals: dict[str, weakref.ReferenceType[Signal]] = {}
        self.ready: dict[str, None] = {}
        self._active: set[str] = set()
        self._timers: Deadlines[str] = Deadlines()
        self._wake: Callable[[], None] | None = None
        self._fault: BaseException | None = None

    def bind_wake(self, wake: Callable[[], None] | None) -> None:
        self._wake = wake
        self._fault = None

    def wake(self) -> None:
        found = self._wake
        if found is None:
            return
        try:
            found()
        except Exception as error:
            self._fault = error

    def take_fault(self) -> BaseException | None:
        fault = self._fault
        self._fault = None
        return fault

    def enqueue(self, actor: str) -> None:
        self._active.add(actor)
        self.ready[actor] = None
        self.wake()

    def unqueue(self, actor: str) -> None:
        self.ready.pop(actor, None)

    def pop(self) -> str | None:
        if not self.ready:
            return None
        actor = next(iter(self.ready))
        del self.ready[actor]
        return actor

    def due(self, now_ms: int) -> None:
        while True:
            actor = self._timers.peek_due(now_ms)
            if actor is None:
                return
            self._timers.remove(actor)
            signal = self.signals.get(actor)
            if signal is None:
                continue
            found = signal()
            if found is not None:
                found.notify(TIMER)

    def update(self, actor: str, deadline: int | None, active: bool, ready: bool) -> None:
        if self._timers.at(actor) != deadline:
            self._timers.remove(actor)
            if deadline is not None:
                self._timers.add(actor, deadline)
        if active:
            self._active.add(actor)
        else:
            self._active.discard(actor)
        if ready:
            self.enqueue(actor)
        else:
            self.unqueue(actor)

    def remove(self, actor: str) -> None:
        self.unqueue(actor)
        self._active.discard(actor)
        self._timers.remove(actor)
        self.signals.pop(actor, None)

    def schedule(self, now_ms: int) -> Schedule:
        deadline = self._timers.next_ms
        return Schedule(
            len(self.ready) > 0 or (deadline is not None and deadline <= now_ms),
            deadline,
            len(self._active) == 0,
        )
