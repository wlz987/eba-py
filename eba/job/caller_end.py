from __future__ import annotations

from eba.envelope.envelope import Envelope, make_envelope
from eba.envelope.ids import EnvelopeId
from eba.envelope.result import err_payload
from eba.errors import MailboxFull
from eba.job.call import _Call
from eba.job.caller import Caller
from eba.job.job import Job
from eba.mail.inbox import enqueue, mark_read, reply_topic


def _end(caller: Caller, job: Job) -> bool:
    call = job.root.payload
    if not isinstance(call, _Call) or call.request_id is None:
        return False
    inbox = caller.inbox
    if inbox.is_closed:
        raise RuntimeError("inbox closed")
    if inbox.remaining() < 1:
        mark_read(inbox)
        raise MailboxFull("target inbox full")
    if not enqueue(
        inbox,
        make_envelope(
            topic=reply_topic(inbox),
            payload=err_payload("cancelled"),
            from_=caller.actor_id,
            cause=job.root.header.cause,
            kind="result",
            correlation_id=call.request_id,
            id_gen=caller._id_gen,
        ),
    ):
        mark_read(inbox)
        raise MailboxFull("target inbox full")
    mark_read(inbox)
    return True


def _mark(caller: Caller, root_id: EnvelopeId) -> bool:
    found = caller.accepted_root(root_id)
    if not isinstance(found, Envelope) or not isinstance(found.payload, _Call):
        return False
    found.payload.cancelled = True
    return True
