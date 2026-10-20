from __future__ import annotations

from eba.envelope.envelope import Envelope
from eba.errors import LeasePending, note_settled
from eba.job.core import Core
from eba.job.ending_settle import _notify as _notify
from eba.job.ending_settle import drop_job as drop_job
from eba.job.ending_settle import invoke as invoke
from eba.job.ending_settle import leave_ending as leave_ending
from eba.job.ending_settle import settle_ending as settle_ending
from eba.job.job import Job, State, become, state_of


def seal_job(core: Core, job: Job) -> None:
    state = state_of(job)
    if state.lifecycle == "active":
        become(state, "delivering")
    core.book.cancel(state.root.header.id)


def release_ending(core: Core, job: Job) -> Envelope:
    state = state_of(job)
    ending = state.pending_control
    try:
        core.book.cancel(state.root.header.id)
    except Exception as error:
        raise LeasePending() from error
    state.pending_control = None
    become(state, "finished")
    if ending is None:
        drop_job(core, job)
        return state.root
    try:
        _notify(job, ending)
    except Exception as error:
        if state_of(job).notice == "finished":
            note_settled(error)
        raise
    finally:
        drop_job(core, job)
    return state.root


def waits_for_book(core: Core, state: State) -> bool:
    return state.pending_control is not None and core.book.count(state.root.header.id) > 0


def waits_for_lease(core: Core) -> bool:
    if not core.book.size:
        return False
    return any(waits_for_book(core, state_of(job)) for job in core.jobs.values())


def release_deferred(core: Core) -> bool:
    released = False
    for job in list(core.jobs.values()):
        state = state_of(job)
        if not waits_for_book(core, state):
            continue
        try:
            release_ending(core, job)
        except RuntimeError as error:
            if isinstance(error, LeasePending):
                continue
            raise
        released = True
    return released
