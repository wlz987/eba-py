from __future__ import annotations

from collections.abc import Callable, Mapping

from eba.envelope.envelope import Envelope
from eba.envelope.ids import EnvelopeId
from eba.envelope.result import Completion, err_payload
from eba.job.job import Context, Job

_STAGE = "reply"


class _Call:
    __slots__ = ("cancelled", "completion", "pay", "payload", "request_id", "timeout_ms", "topic")

    def __init__(
        self,
        topic: str,
        payload: object,
        timeout_ms: int | None,
        pay: Callable[[Completion], None] | None = None,
    ) -> None:
        self.topic = topic
        self.payload = payload
        self.timeout_ms = timeout_ms
        self.request_id: EnvelopeId | None = None
        self.completion: Completion | None = None
        self.cancelled = False
        self.pay = pay

    def complete(self, completion: Completion) -> None:
        if self.completion is not None:
            return
        self.completion = completion
        pay = self.pay
        if pay is not None:
            self.pay = None
            pay(completion)


def _settle(root: Envelope, body: object, request_id: EnvelopeId) -> None:
    call = root.payload
    if not isinstance(call, _Call) or not isinstance(body, Mapping):
        return
    call.complete(Completion(call.request_id or request_id, body))


def settled(envelope: Envelope) -> Completion | None:
    call = envelope.payload
    if not isinstance(call, _Call):
        return None
    return call.completion


class _Wait(Job):
    def begin(self, ctx: Context) -> None:
        call = ctx.root.payload
        if not isinstance(call, _Call):
            raise TypeError("admitted root has no call")
        if call.cancelled:
            self.on_stage_result(ctx, _STAGE, Completion(ctx.root.header.id, err_payload("cancelled")))
            return
        call.request_id = ctx.request(
            stage=_STAGE,
            topic=call.topic,
            payload=call.payload,
            timeout_ms=call.timeout_ms,
        )

    def on_stage_result(self, ctx: Context, _stage: str, completion: Completion) -> None:
        call = ctx.root.payload
        if isinstance(call, _Call):
            call.complete(completion)

    def on_finished(self, body: Mapping[str, object] | None) -> None:
        _settle(self.root, body, self.root.header.id)
