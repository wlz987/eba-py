from __future__ import annotations

from dataclasses import dataclass

from eba.envelope.envelope import Envelope
from eba.envelope.ids import EnvelopeId
from eba.mail.bus import Bus
from eba.mail.inbox import Inbox
from eba.rendezvous.record import Claim
from eba.rendezvous.records import Records


@dataclass(frozen=True, slots=True)
class Continuation:
    owner: EnvelopeId
    stage: str


class RequestBook:
    def __init__(self) -> None:
        self._records = Records()
        self._owners: dict[EnvelopeId, set[EnvelopeId]] = {}
        self._cancelled: list[EnvelopeId] = []

    @property
    def size(self) -> int:
        return self._records.size

    @property
    def next_deadline_ms(self) -> int | None:
        return self._records.next_deadline_ms

    @property
    def unreleased(self) -> int:
        return self._records.unreleased

    def count(self, owner: EnvelopeId) -> int:
        return len(self._owners.get(owner, ()))

    def holds(self, request_id: EnvelopeId) -> bool:
        return self._records.continuation(request_id) is not None

    def submit(
        self,
        bus: Bus,
        inbox: Inbox,
        request: Envelope,
        owner: EnvelopeId,
        stage: str,
        deadline_ms: int | None,
    ) -> None:
        continuation = Continuation(owner, stage)
        try:
            self._records.submit(bus, inbox, request, continuation, deadline_ms)
        finally:
            if self._records.continuation(request.header.id) is continuation:
                self._owners.setdefault(owner, set()).add(request.header.id)

    def take_result(self, envelope: Envelope) -> Claim | None:
        return self._claim(self._records.take_result(envelope))

    def take_due(self, now_ms: int) -> Claim | None:
        return self._claim(self._records.take_due(now_ms))

    def elapse_open(self) -> None:
        self._records.elapse_open()

    def recover(self) -> None:
        self._records.recover()

    def cancel(self, owner: EnvelopeId) -> None:
        for request_id in list(self._owners.get(owner, ())):
            self._records.finish(request_id)
            self._forget(owner, request_id)
            self._cancelled.append(request_id)

    def take_cancelled(self) -> list[EnvelopeId]:
        found = self._cancelled
        self._cancelled = []
        return found

    def _claim(self, claim: Claim | None) -> Claim | None:
        if claim is None:
            return None
        continuation = claim.continuation
        if isinstance(continuation, Continuation):
            self._forget(continuation.owner, claim.completion.request_id)
        return claim

    def _forget(self, owner: EnvelopeId, request_id: EnvelopeId) -> None:
        owned = self._owners.get(owner)
        if owned is not None:
            owned.discard(request_id)
            if not owned:
                del self._owners[owner]
