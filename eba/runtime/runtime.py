from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Literal

from eba.envelope.envelope import IdGen
from eba.job.host import JobHost
from eba.mail.bus import Bus
from eba.mail.inbox import close_count
from eba.notify.agenda import Agenda
from eba.runtime.add import _RuntimeAdd
from eba.runtime.advance import _RuntimeAdvance
from eba.runtime.close import _RuntimeClose
from eba.runtime.context import _ClockView, _Writing
from eba.runtime.drain import _RuntimeDrain
from eba.runtime.lifecycle import _RuntimeLifecycle
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

    @property
    def clock(self) -> Clock:
        return self._clock

    @property
    def id_gen(self) -> IdGen:
        return self._id_gen

    def owns(self, host: JobHost) -> bool:
        return self._hosts.get(str(host.actor_id)) is host

    def bind_wake(self, wake: Callable[[], None] | None) -> None:
        self._agenda.bind_wake(wake)

    def _enter(self) -> AbstractContextManager[None]:
        return _Writing(self)


install_writers(Runtime)
del install_writers
