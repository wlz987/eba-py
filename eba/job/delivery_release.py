from __future__ import annotations

from eba.envelope.envelope import Envelope
from eba.errors import DeliveryError
from eba.job.core import Core
from eba.job.delivery import _complete_held, note_delivery_success, raise_delivery_failure
from eba.job.job import Job
from eba.mail.bus import Bus


def _spent(core: Core, envelope: Envelope) -> bool:
    key = id(envelope)
    return key in core.attempts and key not in core.again


def _parked_job(core: Core, envelope: Envelope) -> Job | None:
    if core.pending is envelope:
        return core.pending_job
    for held, job in core.rest:
        if held is envelope:
            return job
    return None


def retry_due(core: Core) -> bool:
    return core.outbox.has_room() and _next_sendable(core) is not None


def _next_sendable(core: Core) -> tuple[Envelope, Job | None, int] | None:
    if core.pending is not None and not _spent(core, core.pending):
        return core.pending, core.pending_job, -1
    for index, (envelope, job) in enumerate(core.rest):
        if not _spent(core, envelope):
            return envelope, job, index
    return None


def release_result(core: Core, bus: Bus) -> bool:
    sent = False
    while True:
        found = _next_sendable(core)
        if found is None or not core.outbox.has_room():
            return sent
        envelope, job, index = found
        if index < 0:
            core.pending = None
            core.pending_job = None
        else:
            del core.rest[index]
        try:
            core.outbox.send(bus, envelope)
        except DeliveryError as error:
            if index < 0:
                core.pending = envelope
                core.pending_job = job
            else:
                core.rest.insert(index, (envelope, job))
            raise_delivery_failure(core, error)
        if not core.outbox.contains(envelope):
            note_delivery_success(core, envelope)
        _complete_held(core, job)
        sent = True
