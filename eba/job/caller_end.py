from __future__ import annotations

from eba.envelope.envelope import Envelope
from eba.envelope.ids import EnvelopeId
from eba.envelope.result import Completion, err_payload
from eba.job.call import _Call
from eba.job.caller import Caller
from eba.job.ending_settle import drop_job
from eba.job.host_core import core_of
from eba.job.job import Job
from eba.mail.inbox import mark_read


def _end(caller: Caller, job: Job) -> bool:
    call = job.root.payload
    if not isinstance(call, _Call) or call.request_id is None:
        return False
    core = core_of(caller)
    core.book.cancel(job.root.header.id)
    drop_job(core, job)
    mark_read(core.sub.inbox)
    call.complete(Completion(call.request_id, err_payload("cancelled")))
    return True


def _mark(caller: Caller, root_id: EnvelopeId) -> bool:
    found = caller.accepted_root(root_id)
    if not isinstance(found, Envelope) or not isinstance(found.payload, _Call):
        return False
    found.payload.cancelled = True
    return True
