from __future__ import annotations

from eba.envelope.envelope import Envelope
from eba.job.core import Core
from eba.job.pump_refresh import _holding
from eba.notify.signal import READ


def has_work(core: Core) -> bool:
    return (
        core.state == "closing"
        or len(core.jobs) > 0
        or core.queue.size > 0
        or core.book.size > 0
        or core.outbox.size > 0
        or _holding(core)
        or core.book.unreleased > 0
        or core.signal.has(READ)
        or bool(core.abandoned)
    )


def _recv(core: Core) -> Envelope | None:
    if core.sub.inbox.is_closed:
        return None
    return core.sub.try_recv()
