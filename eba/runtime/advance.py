from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING

from eba.envelope.envelope import IdGen
from eba.envelope.ids import EnvelopeId
from eba.errors import DeliveryError, WakeError
from eba.job.held import resolve_held
from eba.job.host import JobHost
from eba.job.host_core import core_of
from eba.mail.inbox import close_count
from eba.time.clock import Clock, pin_clock

if TYPE_CHECKING:
    from eba.mail.bus import Bus
    from eba.notify.agenda import Agenda


class _RuntimeAdvance:
    _hosts: dict[str, JobHost]
    _agenda: Agenda
    _bus: Bus
    _id_gen: IdGen
    _observed: int | None
    _noticed_closes: int

    def _enter(self) -> AbstractContextManager[None]:
        raise NotImplementedError

    _answer_spent: Callable[[DeliveryError, Clock], None]

    def _schedule_now(self) -> int:
        raise NotImplementedError

    def _drain_cancelled(self) -> list[EnvelopeId]:
        cancelled: list[EnvelopeId] = []
        for host in list(self._hosts.values()):
            cancelled.extend(core_of(host).take_cancelled())
        if cancelled:
            for host in list(self._hosts.values()):
                core = core_of(host)
                core.cancel_queued(cancelled)
                core.cancel_held(cancelled)
                core.cancel_jobs(cancelled)
        return cancelled

    def advance(self) -> bool:
        with self._enter():
            try:
                now = self._schedule_now()
                self._observed = now
                noticed = close_count()
                if noticed != self._noticed_closes:
                    self._noticed_closes = noticed
                    for host in list(self._hosts.values()):
                        if host.inbox.is_closed:
                            JobHost.notice_closed_inbox(host)
                            JobHost.project(host, self._agenda)
                self._agenda.due(now)
                if self._drain_cancelled():
                    for host in list(self._hosts.values()):
                        JobHost.project(host, self._agenda)
                pinned = pin_clock(now)
                count = len(self._agenda.ready)
                progressed = False
                for _index in range(count):
                    actor = self._agenda.pop()
                    if actor is None:
                        break
                    host = self._hosts[actor]
                    try:
                        if host.state in {"running", "draining"}:
                            stepped = JobHost.advance(host, self._bus, pinned, self._id_gen)
                            progressed = stepped or progressed
                    except DeliveryError as error:
                        self._answer_spent(error, pinned)
                        raise
                    finally:
                        JobHost.project(host, self._agenda)
                self._drain_cancelled()
                for host in list(self._hosts.values()):
                    if host.state not in {"running", "draining"}:
                        continue
                    try:
                        resolved = resolve_held(core_of(host), self._bus, self._id_gen)
                    except DeliveryError as error:
                        self._answer_spent(error, pinned)
                        raise
                    if resolved:
                        JobHost.project(host, self._agenda)
                        progressed = True
                fault = self._agenda.take_fault()
                if fault is not None:
                    raise WakeError(str(fault)) from fault
                return progressed
            finally:
                self._observed = None
