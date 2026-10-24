from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Literal

from eba.envelope.envelope import IdGen, make_envelope
from eba.job.caller import Caller
from eba.job.host import JobHost
from eba.mail.bus import Bus
from eba.mail.inbox import Inbox, close_count
from eba.notify.agenda import Agenda
from eba.runtime.add import _RuntimeAdd
from eba.runtime.advance import _RuntimeAdvance
from eba.runtime.close import _RuntimeClose
from eba.runtime.context import _ClockView, _Writing
from eba.runtime.drain import _RuntimeDrain
from eba.runtime.lifecycle import _RuntimeLifecycle
from eba.runtime.signals import Pending, _pay
from eba.runtime.spent import _RuntimeSpent
from eba.runtime.view import _RuntimeView
from eba.runtime.writers import install_writers
from eba.time.clock import Clock

_DENIED = "runtime is the only writer"
RuntimeState = Literal["running", "draining", "closing", "closed"]


class Runtime(_RuntimeLifecycle, _RuntimeView, _RuntimeDrain, _RuntimeAdvance, _RuntimeSpent, _RuntimeAdd, _RuntimeClose):
    def __init__(self, bus: Bus, clock: Clock, id_gen: IdGen) -> None:
        self._hosts: dict[str, JobHost] = {}
        self._agenda = Agenda()
        self._busy = False
        self._reading_clock = False
        self._state: RuntimeState = "running"
        self._bus = bus
        self._clock = clock
        self._id_gen = id_gen
        self._view = _ClockView(self)
        self._observed: int | None = None
        self._noticed_closes = close_count()
        self._front_caller: Caller | None = None

    @property
    def clock(self) -> Clock:
        return self._clock

    @property
    def id_gen(self) -> IdGen:
        return self._id_gen

    def ask(
        self,
        topic: str,
        payload: object,
        from_: str = "caller",
        timeout_ms: int | None = None,
    ) -> Pending:
        caller = self._front_caller
        if caller is None:
            caller = Caller(Inbox(8).receiver(), self._id_gen, actor_id="sys.ask")
            self.add(caller)
            self._front_caller = caller
        loop = asyncio.get_running_loop()
        ready = loop.create_future()
        envelope = caller.admit(
            topic=topic,
            payload=payload,
            from_=from_,
            timeout_ms=timeout_ms,
            pay=_pay(ready),
        )
        return Pending(envelope, ready)

    def tell(self, topic: str, payload: object, from_: str = "caller") -> None:
        envelope = make_envelope(
            topic=topic,
            payload=payload,
            from_=from_,
            id_gen=self._id_gen,
            kind="event",
        )
        self._bus.publish(envelope)

    def owns(self, host: JobHost) -> bool:
        return self._hosts.get(str(host.actor_id)) is host

    def bind_wake(self, wake: Callable[[], None] | None) -> None:
        self._agenda.bind_wake(wake)

    def _enter(self) -> AbstractContextManager[None]:
        return _Writing(self)


install_writers(Runtime)
del install_writers
