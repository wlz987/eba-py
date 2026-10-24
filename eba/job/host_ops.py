from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from eba.envelope.envelope import Envelope, IdGen
from eba.envelope.ids import EnvelopeId
from eba.job.host_core import core_of
from eba.job.host_ops_query import _HostOpsQuery
from eba.job.pump import advance_host, arm_closed_waits, attach_core, has_work, scheduled
from eba.job.resume import resume
from eba.job.turn import require
from eba.mail.bus import Bus
from eba.notify.agenda import Agenda
from eba.time.clock import Clock

if TYPE_CHECKING:
    from eba.job.host import JobHost


class _HostOps(_HostOpsQuery):
    def attach(self, bus: Bus) -> None:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), _sheet=("eba-sheet",))
        attach_core(core, bus)

    def withdraw(self) -> None:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), _sheet=("eba-sheet",))
        core.sub.stop()

    def bind(self, agenda: Agenda, actor: str) -> None:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), owned=True, _sheet=("eba-sheet",))
        core.signal.bind(agenda, actor)

    def unbind(self) -> None:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), owned=True, _sheet=("eba-sheet",))
        core.signal.detach()

    def on_step(self, _clock: Clock) -> None:
        return None

    def advance(self, bus: Bus, clock: Clock, id_gen: IdGen) -> bool:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), _sheet=("eba-sheet",))
        self.on_step(clock)
        return advance_host(core, bus, clock, id_gen)

    def notice_closed_inbox(self) -> None:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), owned=True, _sheet=("eba-sheet",))
        arm_closed_waits(core)

    def project(self, agenda: Agenda) -> None:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), owned=True, _sheet=("eba-sheet",))
        closing = core.state == "closing"
        retired = core.state == "closed"
        agenda.update(
            str(core.sub.actor_id),
            None if closing or retired else core.book.next_deadline_ms,
            closing or (not retired and has_work(core)),
            not closing and not retired and scheduled(core),
        )

    def delivery_spent(self, envelope: Envelope) -> bool:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), owned=True, _sheet=("eba-sheet",))
        key = id(envelope)
        return key in core.attempts and key not in core.again

    def resume_held(
        self,
        request_id: EnvelopeId,
        failure: Envelope,
        bus: Bus,
        clock: Clock,
        id_gen: IdGen,
        after: Callable[[], None],
    ) -> bool:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), owned=True, _sheet=("eba-sheet",))
        if not core.book.holds(request_id):
            return False
        if core.busy or core.state not in {"running", "draining"}:
            return True
        try:
            resume(core, bus, clock, id_gen, failure)
        finally:
            after()
        return True
