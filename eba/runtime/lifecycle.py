from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager

from eba.envelope.envelope import IdGen
from eba.envelope.ids import ActorId
from eba.job.host import JobHost
from eba.mail.bus import Bus
from eba.notify.agenda import Agenda
from eba.time.clock import Clock
from eba.time.schedule import Schedule

_DENIED = "runtime is the only writer"


class _RuntimeLifecycle:
    _hosts: dict[str, JobHost]
    _bus: Bus
    _clock: Clock
    _id_gen: IdGen
    _agenda: Agenda
    _busy: bool
    _reading_clock: bool
    _state: str
    _noticed_closes: int
    _observed: int | None

    def _enter(self) -> AbstractContextManager[None]:
        raise NotImplementedError

    _select: Callable[[ActorId | str | None], list[JobHost]]

    _schedule_now: Callable[[], int]

    def schedule(self) -> Schedule:
        now_ms = self._schedule_now()
        snapshot = self._agenda.schedule(now_ms)
        return Schedule(
            not self._busy and snapshot.ready,
            snapshot.next_deadline_ms,
            not self._busy and snapshot.is_quiescent,
            now_ms=now_ms,
        )
