from __future__ import annotations

from typing import NoReturn

from eba.envelope.envelope import Envelope
from eba.errors import DeliveryError, OutboxFull, combine_failures
from eba.job.core import Core
from eba.job.ending import settle_ending, waits_for_book
from eba.job.job import Job, state_of
from eba.mail.bus import Bus


def release_attempts(core: Core) -> None:
    core.attempts.clear()
    core.again.clear()
    core.kept.clear()


def note_delivery_failure(core: Core, envelope: Envelope) -> None:
    if not _owns(core, envelope):
        return
    key = id(envelope)
    count = core.attempts.get(key, 0) + 1
    if count < 2:
        _keep(core, envelope, count, retry=True)
        core.outbox.rearm(envelope)
        return
    job = _parked_job(core, envelope)
    _keep(core, envelope, count, retry=False)
    _unpark(core, envelope)
    core.outbox.bury(envelope)
    _complete_held(core, job)


def note_delivery_success(core: Core, envelope: Envelope) -> None:
    _forget(core, envelope)


def holds_letter(core: Core, envelope: Envelope) -> bool:
    if core.pending is envelope:
        return True
    return any(held is envelope for held, _job in core.rest)


def hold_or_send(core: Core, bus: Bus, job: Job | None, envelope: Envelope) -> bool:
    try:
        core.outbox.send(bus, envelope)
        return True
    except DeliveryError as error:
        full = isinstance(error, OutboxFull)
        _park(core, job, envelope)
        if full:
            return False
        raise_delivery_failure(core, error)


def raise_delivery_failure(core: Core, error: DeliveryError) -> NoReturn:
    try:
        note_delivery_failure(core, error.envelope)
    except Exception as secondary:
        raise combine_failures(error, secondary)  # noqa: B904
    raise error


def _complete_held(core: Core, job: Job | None) -> None:
    if job is None:
        return
    state = state_of(job)
    if waits_for_book(core, state):
        return
    control = state.pending_control
    state.pending_control = None
    if control is not None:
        settle_ending(core, job, control)


from eba.job.delivery_park import _forget as _forget  # noqa: E402
from eba.job.delivery_park import _keep as _keep  # noqa: E402
from eba.job.delivery_park import _owns as _owns  # noqa: E402
from eba.job.delivery_park import _park as _park  # noqa: E402
from eba.job.delivery_park import _unpark as _unpark  # noqa: E402
from eba.job.delivery_release import _parked_job  # noqa: E402
from eba.job.delivery_release import release_result as release_result  # noqa: E402
from eba.job.delivery_release import retry_due as retry_due  # noqa: E402
