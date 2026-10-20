from __future__ import annotations

from eba.envelope.ids import EnvelopeId
from eba.rendezvous.lease import _Lease, _Route
from eba.rendezvous.lease import _matched as _matched
from eba.rendezvous.record import _Record
from eba.rendezvous.records_finish import _RecordsFinish
from eba.rendezvous.records_routes import _RecordsRoutes
from eba.rendezvous.records_submit import _RecordsSubmit
from eba.rendezvous.records_take import UnreadableResult as UnreadableResult
from eba.rendezvous.records_take import _RecordsTake
from eba.time.deadlines import ELAPSED, Deadlines


class Records(_RecordsRoutes, _RecordsTake, _RecordsFinish, _RecordsSubmit):
    def __init__(self) -> None:
        self._entries: dict[EnvelopeId, _Record] = {}
        self._deadlines: Deadlines[EnvelopeId] = Deadlines()
        self._routes: dict[int, dict[str, _Route]] = {}
        self._stuck: list[_Lease] = []

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def next_deadline_ms(self) -> int | None:
        return self._deadlines.next_ms

    def elapse_open(self) -> None:
        for request_id in list(self._entries):
            if self._deadlines.at(request_id) is None:
                self._deadlines.add(request_id, ELAPSED)

    @property
    def unreleased(self) -> int:
        return len(self._stuck)

    def continuation(self, request_id: EnvelopeId) -> object | None:
        record = self._entries.get(request_id)
        if record is None:
            return None
        return record.continuation

    def recover(self) -> None:
        self._recover_owed()

    def finish(self, request_id: EnvelopeId, *, claim: bool = False) -> _Record | None:
        self._recover_owed()
        record = self._entries.get(request_id)
        if record is None:
            return None
        routes = self._routes[record.inbox.id]
        route = routes[record.topic]
        closed = True
        if route.count == 1:
            before = route.bus.subscription_count(record.topic, record.inbox)
            try:
                route.subscription.close()
            except Exception:
                if not claim:
                    raise
                released = (not route.owner.active()) or route.bus.subscription_count(record.topic, record.inbox) < before
                closed = released
                if not closed:
                    self._owe(route.lease)
        del self._entries[request_id]
        self._deadlines.remove(request_id)
        route.bus.release_wait(request_id)
        remaining = route.count - 1
        if remaining == 0 and closed:
            self._drop_route(record.inbox.id, record.topic)
            self._paid(route.lease)
        elif remaining == 0:
            routes[record.topic] = _Route(route.lease, 0, route.bus)
        else:
            routes[record.topic] = _Route(route.lease, remaining, route.bus)
        if claim:
            self._recover_owed()
        return record
