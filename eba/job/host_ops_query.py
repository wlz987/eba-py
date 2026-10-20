from __future__ import annotations

from typing import TYPE_CHECKING, cast

from eba.envelope.envelope import Envelope
from eba.envelope.ids import EnvelopeId
from eba.errors import Reentrant
from eba.job.host_core import core_of
from eba.mail.inbox import find
from eba.mail.queue import Queue

if TYPE_CHECKING:
    from eba.job.host import JobHost


def _queued(queue: Queue, root_id: EnvelopeId) -> Envelope | None:
    for item in queue:
        if isinstance(item, Envelope) and item.header.id == root_id:
            return item
    return None


class _HostOpsQuery:
    def require_idle(self) -> None:
        if core_of(cast("JobHost", self)).busy:
            raise Reentrant()

    def crowded(self) -> bool:
        core = core_of(cast("JobHost", self))
        inbox = core.sub.inbox
        sitting = 0 if inbox.is_closed else inbox.capacity - inbox.remaining()
        held = len(core.jobs) + core.queue.size + sitting
        return held >= core.active_limit

    def accepted_root(self, root_id: EnvelopeId) -> Envelope | None:
        core = core_of(cast("JobHost", self))
        return find(core.sub.inbox, root_id) or _queued(core.queue, root_id)
