from __future__ import annotations

from eba.envelope.envelope import Envelope
from eba.errors import LeasePending, combine_failures
from eba.job.close_ops import _finish_jobs, _settle_inbound, _settle_letter
from eba.job.core import Core
from eba.job.delivery import release_attempts
from eba.job.held import close_held
from eba.job.job import state_of
from eba.job.pump import _SIGNAL_MASK, _enter, _idle, _recompute_pause
from eba.mail.bus import Bus
from eba.mail.inbox import held_count, take_seized


def close_core(core: Core, bus: Bus) -> list[Envelope]:
    if core.state == "closed":
        return list(core.abandoned or [])
    _enter(core, closing=True)
    try:
        abandoned = core.begin_close()
        close_held(core)
        hook_error, lease_error = _finish_jobs(core, abandoned)
        _settle_inbound(core, abandoned, core.queue.size + held_count(core.sub.inbox))
        _recompute_pause(core)
        if lease_error is not None:
            if hook_error is not None:
                raise combine_failures(hook_error, lease_error)
            raise lease_error
        core.book.recover()
        if core.book.unreleased or core.book.size:
            pending = LeasePending()
            if hook_error is not None:
                raise combine_failures(hook_error, pending)
            raise pending
        core.outbox.drain(abandoned)
        while core.pending is not None or core.rest:
            if core.pending is None:
                envelope, job = core.rest.popleft()
            else:
                envelope = core.pending
                job = core.pending_job
                core.pending = None
                core.pending_job = None
            if job is None:
                _settle_letter(core, envelope, abandoned, notify=True)
                continue
            state = state_of(job)
            state.pending_control = None
            if state.notice == "finished":
                abandoned.append(envelope)
            else:
                _settle_letter(core, envelope, abandoned, notify=True)
        core.sub.close(bus)
        for envelope in take_seized(core.sub.inbox):
            abandoned.append(envelope)
        core.signal.clear(_SIGNAL_MASK)
        core.state = "closed"
        release_attempts(core)
        if hook_error is not None:
            raise hook_error
        return abandoned
    finally:
        _idle(core)
