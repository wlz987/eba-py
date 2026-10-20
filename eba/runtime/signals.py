from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, NamedTuple

from eba.envelope.envelope import Envelope
from eba.envelope.result import Completion
from eba.mail.inbox import Inbox
from eba.notify.signal import Signal
from eba.notify.watch import Interest

if TYPE_CHECKING:
    from eba.runtime.drive import Drive


class Pending(NamedTuple):
    envelope: Envelope
    ready: asyncio.Future[Completion]


def _pay(future: asyncio.Future[Completion]) -> Callable[[Completion], None]:

    def deliver(completion: Completion) -> None:
        if not future.done():
            future.set_result(completion)

    return deliver


class _Signal:
    __slots__ = ("_fired", "_waiter")

    def __init__(self) -> None:
        self._fired = False
        self._waiter: asyncio.Future[None] | None = None

    def fire(self) -> None:
        self._fired = True
        waiter = self._waiter
        if waiter is not None and not waiter.done():
            waiter.set_result(None)

    def consume(self) -> bool:
        fired, self._fired = self._fired, False
        return fired

    def arm(self, waiter: asyncio.Future[None]) -> None:
        self._waiter = waiter
        if self._fired and not waiter.done():
            waiter.set_result(None)

    def disarm(self, waiter: asyncio.Future[None]) -> None:
        if self._waiter is waiter:
            self._waiter = None

    def expire(self, waiter: asyncio.Future[None]) -> None:
        if self._waiter is waiter and not waiter.done():
            waiter.set_result(None)


class _SpaceKick(Interest):
    def __init__(self, drive: Drive, inbox: Inbox) -> None:
        super().__init__(Signal(), {}, "")
        self._drive = drive
        self._inbox = inbox

    def notify(self) -> None:
        self._drive._space_kicks.pop(id(self._inbox), None)
        self._drive._wake.fire()
