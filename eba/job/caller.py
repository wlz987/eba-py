from __future__ import annotations

from collections.abc import Callable

from eba.envelope.envelope import Envelope, IdGen, make_envelope
from eba.envelope.ids import ActorId, EnvelopeId, envelope_id
from eba.envelope.result import Completion, err_payload
from eba.envelope.topic import split_topic
from eba.errors import BackpressureError, MailboxFull
from eba.job.call import _Call, _settle, _Wait
from eba.job.call import settled as settled
from eba.job.host import JobHost
from eba.job.job import Job
from eba.mail.inbox import Receiver, can_enqueue, enqueue, mark_read, reply_topic
from eba.time.numbers import nonnegative_int

_ADMIT = "sys.admit"


class Caller(JobHost):
    def __init__(
        self,
        receiver: Receiver,
        id_gen: IdGen,
        active_limit: int = 256,
    ) -> None:
        super().__init__(
            actor_id="caller",
            receiver=receiver,
            patterns=(),
            active_limit=active_limit,
        )
        self._id_gen = id_gen

    def make_job(self, root: Envelope) -> Job:
        return _Wait(root)

    def on_rejected(self, root: Envelope, reason: str) -> None:
        _settle(root, err_payload(reason), root.header.id)

    def admit(
        self,
        *,
        topic: str,
        payload: object,
        from_: ActorId | str,
        timeout_ms: int | None = None,
        pay: Callable[[Completion], None] | None = None,
    ) -> Envelope:
        self.require_idle()
        inbox = self.inbox
        if inbox.is_closed:
            raise RuntimeError("inbox closed")
        if self.state == "draining":
            raise RuntimeError("host draining")
        if self.state != "running":
            raise RuntimeError("host closing")
        if timeout_ms is not None:
            nonnegative_int(timeout_ms, "timeout_ms")
        split_topic(topic)
        if self.crowded():
            raise BackpressureError("active_full")
        if not can_enqueue(inbox, "request"):
            raise MailboxFull("target inbox full")
        request = make_envelope(
            topic=_ADMIT,
            payload=_Call(topic, payload, timeout_ms, pay),
            from_=from_,
            id_gen=self._id_gen,
            kind="request",
            reply_to=reply_topic(inbox),
        )
        if not enqueue(inbox, request):
            raise MailboxFull("target inbox full")
        mark_read(inbox)
        return request

    def cancel(self, root_id: EnvelopeId | str) -> bool:
        self.require_idle()
        if self.state in {"closing", "closed"}:
            raise RuntimeError("host closing")
        chosen = envelope_id(root_id)
        job = self.job(chosen)
        if job is not None:
            return _end(self, job)
        return _mark(self, chosen)


from eba.job.caller_end import _end as _end  # noqa: E402
from eba.job.caller_end import _mark as _mark  # noqa: E402
