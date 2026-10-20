from __future__ import annotations

from typing import TYPE_CHECKING, cast

from eba.envelope.envelope import Envelope
from eba.envelope.ids import ActorId, EnvelopeId
from eba.job.core import HostState
from eba.job.host_core import core_of
from eba.job.job import Job
from eba.job.pump import has_work
from eba.mail.inbox import Inbox

if TYPE_CHECKING:
    from eba.job.host import JobHost


class _HostView:
    @property
    def actor_id(self) -> ActorId:
        return core_of(cast("JobHost", self)).sub.actor_id

    @property
    def inbox(self) -> Inbox:
        return core_of(cast("JobHost", self)).sub.inbox

    @property
    def state(self) -> HostState:
        return core_of(cast("JobHost", self)).state

    def make_job(self, root: Envelope) -> Job:
        raise NotImplementedError("make_job")

    def on_rejected(self, _root: Envelope, _reason: str) -> None:
        return None

    def job(self, request_id: EnvelopeId) -> Job | None:
        return core_of(cast("JobHost", self)).jobs.get(request_id)

    @property
    def active_count(self) -> int:
        return len(core_of(cast("JobHost", self)).jobs)

    @property
    def queued_count(self) -> int:
        return core_of(cast("JobHost", self)).queue.size

    @property
    def pending_count(self) -> int:
        return core_of(cast("JobHost", self)).book.size

    @property
    def unsent_count(self) -> int:
        return core_of(cast("JobHost", self)).outbox.size

    @property
    def rejected_count(self) -> int:
        return core_of(cast("JobHost", self)).rejected_count

    @property
    def next_deadline_ms(self) -> int | None:
        return core_of(cast("JobHost", self)).book.next_deadline_ms

    @property
    def is_quiescent(self) -> bool:
        core = core_of(cast("JobHost", self))
        return not core.busy and not has_work(core)

    @property
    def admitted(self) -> bool:
        return core_of(cast("JobHost", self)).signal.is_bound
