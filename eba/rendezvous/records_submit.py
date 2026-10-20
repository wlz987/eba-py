from __future__ import annotations

from eba.envelope.envelope import Envelope, checked_envelope
from eba.envelope.errors import EnvelopeBuildError
from eba.envelope.header import Request
from eba.envelope.ids import EnvelopeId
from eba.errors import combine_failures
from eba.mail.bus import Bus
from eba.mail.inbox import Inbox
from eba.rendezvous.lease import _Closable, _granted_owner, _Lease, _noted, _Route
from eba.rendezvous.record import _Record
from eba.time.deadlines import ELAPSED, Deadlines
from eba.time.numbers import nonnegative_int


class _RecordsSubmit:
    _entries: dict[EnvelopeId, _Record]
    _routes: dict[int, dict[str, _Route]]
    _deadlines: Deadlines[EnvelopeId]

    def _ensure_routes(self, inbox_id: int) -> dict[str, _Route]:
        raise NotImplementedError

    def _drop_route(self, inbox_id: int, topic: str) -> None:
        raise NotImplementedError

    def _paid(self, lease: _Lease) -> None:
        raise NotImplementedError

    def _roll_back(self, granted: _Closable | None, frame: list[tuple[int, object]], inbox_id: int) -> None:
        raise NotImplementedError

    def submit(
        self,
        bus: Bus,
        inbox: Inbox,
        request: Envelope,
        continuation: object,
        deadline_ms: int | None,
    ) -> None:
        request = checked_envelope(request)
        header = request.header
        address = header.address
        if not isinstance(address, Request):
            raise EnvelopeBuildError("expected a request with reply_to")
        reply_to = address.reply_to
        if header.id in self._entries:
            raise EnvelopeBuildError(f"duplicate request id: {header.id}")
        if deadline_ms is not None:
            nonnegative_int(deadline_ms, "deadline_ms")
        if inbox.is_closed:
            raise RuntimeError("inbox closed")
        routes = self._ensure_routes(inbox.id)
        route = routes.get(reply_to)
        if route is not None and route.count == 0 and not route.owner.active():
            self._paid(route.lease)
            self._drop_route(inbox.id, reply_to)
            route = None
        if route is None:
            routes = self._ensure_routes(inbox.id)
            with bus.granting() as frame:
                granted = None
                try:
                    granted = bus.subscribe(reply_to, inbox)
                    owner = _granted_owner(granted, _noted(inbox.id, frame))
                    route = _Route(_Lease(granted, owner), 0, bus)
                except Exception:
                    self._roll_back(granted, frame, inbox.id)
                    if not routes:
                        self._routes.pop(inbox.id, None)
                    raise
        route = _Route(route.lease, route.count + 1, route.bus)
        routes[reply_to] = route
        self._entries[header.id] = _Record(reply_to, header.cause, continuation, inbox)
        bus.hold_wait(header.id)
        try:
            delivered = bus.publish(request)
            due = deadline_ms
            if delivered is False and due is None:
                due = ELAPSED
            if due is not None:
                self._deadlines.add(header.id, due)
        except Exception as error:
            try:
                self.finish(header.id)
            except Exception as secondary:
                raise combine_failures(error, secondary)  # noqa: B904
            raise

    def finish(self, request_id: EnvelopeId, *, claim: bool = False) -> _Record | None:
        raise NotImplementedError
