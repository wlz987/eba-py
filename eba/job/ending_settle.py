from __future__ import annotations

import inspect
from collections.abc import Callable

from eba.errors import note_settled
from eba.job.core import Core
from eba.job.job import Control, Job, become, state_of


def invoke(callback: Callable[[], object]) -> None:
    returned = callback()
    if inspect.iscoroutine(returned):
        returned.close()
        raise TypeError("Job hooks must be synchronous and return None")
    if returned is not None:
        raise TypeError("Job hooks must be synchronous and return None")


def drop_job(core: Core, job: Job) -> None:
    request_id = state_of(job).root.header.id
    reply = core.held.pop(request_id, None)
    if reply is not None:
        reply._close()
    if core.jobs.get(request_id) is job:
        del core.jobs[request_id]


def _notify(job: Job, control: Control) -> None:
    state = state_of(job)
    become(state, "finished")
    state.notice = "finished"
    invoke(lambda: job.on_finished(control.body))


def leave_ending(job: Job, control: Control | None) -> None:
    if control is not None:
        state_of(job).pending_control = control


def settle_ending(core: Core, job: Job, control: Control | None) -> None:
    if control is None:
        return
    try:
        _notify(job, control)
    except Exception as error:
        if state_of(job).notice == "finished":
            note_settled(error)
        raise
    finally:
        drop_job(core, job)
