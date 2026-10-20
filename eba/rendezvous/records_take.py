from __future__ import annotations

from eba.envelope.envelope import Envelope, checked_envelope
from eba.envelope.errors import EnvelopeBuildError
from eba.envelope.ids import EnvelopeId
from eba.envelope.result import Completion, result_body, result_request_id
from eba.rendezvous.record import Claim, _Record
from eba.time.deadlines import Deadlines
from eba.time.numbers import nonnegative_int


class UnreadableResult(Exception):
    pass


class _RecordsTake:
    _entries: dict[EnvelopeId, _Record]
    _deadlines: Deadlines[EnvelopeId]

    def take_result(self, envelope: Envelope) -> Claim | None:
        try:
            envelope = checked_envelope(envelope)
        except (EnvelopeBuildError, TypeError, AttributeError) as error:
            raise UnreadableResult() from error
        request_id = result_request_id(envelope)
        record = None if request_id is None else self._entries.get(request_id)
        if (
            request_id is None
            or record is None
            or record.topic != envelope.header.topic
            or record.cause != envelope.header.cause
        ):
            return None
        try:
            body = result_body(envelope)
        except Exception as error:
            raise UnreadableResult() from error
        if body is None:
            raise UnreadableResult()
        claimed = self.finish(request_id, claim=True)
        if claimed is None:
            return None
        return Claim(claimed.continuation, Completion(request_id, body))

    def take_due(self, now_ms: int) -> Claim | None:
        nonnegative_int(now_ms, "clock_ms")
        request_id = self._deadlines.peek_due(now_ms)
        if request_id is None:
            return None
        record = self.finish(request_id, claim=True)
        if record is None:
            return None
        return Claim(record.continuation, Completion(request_id, None))

    def finish(self, request_id: EnvelopeId, *, claim: bool = False) -> _Record | None:
        raise NotImplementedError
