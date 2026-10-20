from __future__ import annotations

from typing import TYPE_CHECKING

from eba.envelope.ids import ActorId
from eba.job.host import JobHost
from eba.time.clock import Clock, read_clock

if TYPE_CHECKING:
    pass


class _RuntimeView:
    _observed: int | None
    _reading_clock: bool
    _clock: Clock
    _view: Clock
    _hosts: dict[str, JobHost]

    def _schedule_now(self) -> int:
        if self._observed is not None:
            return self._observed
        return read_clock(self._clock_view())

    def _now(self) -> int:
        if self._reading_clock:
            raise RuntimeError("reentrant clock observation")
        self._reading_clock = True
        try:
            return self._clock.now_ms()
        finally:
            self._reading_clock = False

    def _clock_view(self) -> Clock:
        return self._view

    def _select(self, actor_id: ActorId | str | None) -> list[JobHost]:
        if actor_id is None:
            return list(self._hosts.values())
        host = self._hosts.get(str(actor_id))
        if host is None:
            raise RuntimeError(f"unknown host: {actor_id}")
        return [host]
