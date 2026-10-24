from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Literal

from eba.envelope.envelope import Envelope, IdGen, make_envelope
from eba.envelope.result import Completion
from eba.job.caller import Caller
from eba.job.host import JobHost
from eba.job.host_core import core_of
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
        bus.claim(self)
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
        loop = asyncio.get_running_loop()
        ready = loop.create_future()
        envelope = self._front().admit(
            topic=topic,
            payload=payload,
            from_=from_,
            timeout_ms=timeout_ms,
            pay=_pay(ready),
        )
        return Pending(envelope, ready)

    def ask_with(
        self,
        topic: str,
        payload: object,
        from_: str = "caller",
        timeout_ms: int | None = None,
        *,
        pay: Callable[[Completion], None],
    ) -> Envelope:
        """Hand the completion to pay; it runs once inside a turn and must not re-enter the runtime."""
        return self._front().admit(
            topic=topic,
            payload=payload,
            from_=from_,
            timeout_ms=timeout_ms,
            pay=pay,
        )

    def _front(self) -> Caller:
        caller = self._front_caller
        if caller is None:
            # front inbox matches Caller's default active limit
            caller = Caller(Inbox(256).receiver(), self._id_gen, actor_id="sys.ask")
            self.add(caller)
            self._front_caller = caller
        return caller

    def tell(self, topic: str, payload: object, from_: str = "caller") -> None:
        envelope = make_envelope(
            topic=topic,
            payload=payload,
            from_=from_,
            id_gen=self._id_gen,
            kind="event",
        )
        self._bus.publish(envelope)

    def stats(self) -> dict[str, int | str | None]:
        active = held = queued = pending = rejected = cancel_errors = pending_cancels = 0
        last: str | None = None
        for host in self._hosts.values():
            core = core_of(host)
            active += len(core.jobs)
            held += len(core.held)
            queued += core.queue.size
            pending += core.book.size
            rejected += core.rejected_count
            cancel_errors += core.cancel_errors
            pending_cancels += len(core.cancel_pending)
            last = core.last_cancel_error or last
        return {
            "hosts": len(self._hosts),
            "active": active,
            "held": held,
            "queued": queued,
            "pending": pending,
            "rejected": rejected,
            "cancel_errors": cancel_errors,
            "pending_cancels": pending_cancels,
            "last_cancel_error": last,
        }

    def owns(self, host: JobHost) -> bool:
        return self._hosts.get(str(host.actor_id)) is host

    def bind_wake(self, wake: Callable[[], None] | None) -> None:
        self._agenda.bind_wake(wake)

    def _enter(self) -> AbstractContextManager[None]:
        return _Writing(self)


install_writers(Runtime)
del install_writers
