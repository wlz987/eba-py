from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING

from eba.envelope.envelope import Envelope
from eba.envelope.ids import ActorId
from eba.errors import combine_failures
from eba.job.host import JobHost
from eba.job.turn import require
from eba.mail.bus import Bus
from eba.notify.agenda import Agenda

if TYPE_CHECKING:
    pass


class _RuntimeClose:
    _state: str
    _bus: Bus
    _agenda: Agenda
    _hosts: dict[str, JobHost]
    _select: Callable[[ActorId | str | None], list[JobHost]]
    _enter: Callable[[], AbstractContextManager[None]]

    def close(self, actor_id: ActorId | str | None = None) -> list[Envelope]:
        if self._state == "closed":
            return []
        entered = False
        try:
            with self._enter():
                entered = True
                selected = self._select(actor_id)
                if actor_id is None:
                    self._state = "closing"
                    for host in selected:
                        JobHost.begin_close(host)
                failed: Exception | None = None
                for host in selected:
                    try:
                        JobHost.close_owned(host, self._bus)
                    except Exception as error:
                        failed = error if failed is None else combine_failures(failed, error)
                        if host.state != "closed":
                            raise failed  # noqa: B904
                    finally:
                        JobHost.project(host, self._agenda)
                if failed is not None:
                    raise failed
                abandoned: list[Envelope] = []
                for host in selected:
                    abandoned.extend(JobHost.take_abandoned(host))
                    JobHost.unbind(host)
                    actor = str(host.actor_id)
                    self._agenda.remove(actor)
                    self._hosts.pop(actor, None)
                    require(host, op="release")
                if actor_id is None:
                    self._state = "closed"
                    self._bus.release(self)
                return abandoned
        finally:
            if entered:
                self._agenda.wake()
