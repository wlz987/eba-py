from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING

from eba.errors import combine_failures
from eba.job.host import JobHost
from eba.job.turn import require

if TYPE_CHECKING:
    from eba.mail.bus import Bus
    from eba.notify.agenda import Agenda


class _RuntimeAdd:
    _state: str
    _hosts: dict[str, JobHost]
    _agenda: Agenda
    _bus: Bus

    def _enter(self) -> AbstractContextManager[None]:
        raise NotImplementedError

    def add(self, host: JobHost) -> None:
        with self._enter():
            if self._state != "running":
                raise RuntimeError("runtime cannot accept hosts")
            if host.admitted:
                raise RuntimeError("host already admitted")
            actor = str(host.actor_id)
            if actor in self._hosts:
                raise RuntimeError("duplicate host actor")
            require(host, op="admit")
            JobHost.attach(host, self._bus)
            self._hosts[actor] = host
            require(host, op="claim")
            JobHost.bind(host, self._agenda, actor)
            JobHost.project(host, self._agenda)
            if self._state != "running":
                refused = RuntimeError("runtime cannot accept hosts")
                del self._hosts[actor]
                self._agenda.remove(actor)
                try:
                    JobHost.unbind(host)
                    try:
                        JobHost.withdraw(host)
                    except Exception as stuck:
                        raise combine_failures(refused, stuck) from stuck
                    raise refused
                finally:
                    require(host, op="release")
