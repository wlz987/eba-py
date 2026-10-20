from __future__ import annotations

from collections import deque

from eba.envelope.envelope import Envelope
from eba.job.core import Core
from eba.job.delivery import holds_letter
from eba.job.job import Job


def _park(core: Core, job: Job | None, envelope: Envelope) -> None:
    if core.pending is None:
        core.pending = envelope
        core.pending_job = job
    else:
        core.rest.append((envelope, job))


def _owns(core: Core, envelope: Envelope) -> bool:
    return holds_letter(core, envelope) or core.outbox.contains(envelope)


def _keep(core: Core, envelope: Envelope, count: int, *, retry: bool) -> None:
    key = id(envelope)
    core.attempts[key] = count
    core.kept[key] = envelope
    if retry:
        core.again.add(key)
        return
    core.again.discard(key)


def _forget(core: Core, envelope: Envelope) -> None:
    key = id(envelope)
    core.attempts.pop(key, None)
    core.again.discard(key)
    core.kept.pop(key, None)


def _unpark(core: Core, envelope: Envelope) -> None:
    if core.pending is envelope:
        core.pending = None
        core.pending_job = None
    kept: deque[tuple[Envelope, Job | None]] = deque()
    for held, job in core.rest:
        if held is not envelope:
            kept.append((held, job))
    core.rest = kept
