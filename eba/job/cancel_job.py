from __future__ import annotations

from typing import TYPE_CHECKING

from eba.envelope.result import err_payload
from eba.job.ending import drop_job, invoke, seal_job
from eba.job.job import Job, become, state_of

if TYPE_CHECKING:
    from eba.job.core import Core


def cancel_job(core: Core, job: Job) -> bool:
    state = state_of(job)
    if state.lifecycle != "active" or state.held:
        return False
    body = err_payload("cancelled")
    become(state, "finished")
    state.notice = "finished"
    error: Exception | None = None
    try:
        invoke(lambda: job.on_finished(body))
    except Exception as cause:
        error = cause
    try:
        seal_job(core, job)
    except Exception as cause:
        if error is None:
            error = cause
    finally:
        drop_job(core, job)
    if error is not None:
        core.cancel_errors += 1
        core.last_cancel_error = str(error)
    return True
