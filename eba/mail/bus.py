from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from eba.envelope.envelope import Envelope
from eba.envelope.errors import EnvelopeBuildError
from eba.envelope.topic import split_topic
from eba.mail.bus_deliver import _BusDeliver, _Offer
from eba.mail.inbox import (
    Inbox,
    can_enqueue,
    watch_space,
)
from eba.mail.routes import Subscription as Subscription
from eba.mail.routes import _Routes
from eba.notify.watch import Interest
from eba.pattern import parse_pattern


class Bus(_BusDeliver):
    def __init__(self) -> None:
        self._routes = _Routes()
        self._grant_frames: list[list[tuple[int, object]]] = []
        self._offers: list[_Offer] = []
        self._waits: set[str] = set()

    @contextmanager
    def granting(self) -> Iterator[list[tuple[int, object]]]:
        frame: list[tuple[int, object]] = []
        self._grant_frames.append(frame)
        try:
            yield frame
        finally:
            self._grant_frames.pop()

    def note_grant(self, inbox: Inbox, granted: object) -> None:
        if self._grant_frames:
            self._grant_frames[-1].append((inbox.id, granted))

    def hold_wait(self, request_id: str) -> None:
        self._waits.add(request_id)

    def release_wait(self, request_id: str) -> None:
        self._waits.discard(request_id)

    def waiting(self, request_id: str | None) -> bool:
        return request_id is not None and request_id in self._waits

    def subscribe(self, pattern: str, inbox: Inbox) -> Subscription:
        if inbox.is_closed:
            raise RuntimeError("inbox closed")
        parsed = parse_pattern(pattern)
        self._routes.subscribe(parsed, inbox)

        def release() -> bool:
            found, pending = self._routes._detach(parsed, inbox, granted)
            if pending is not None:
                self._routes.changes.notify(pending)
            return found

        granted = Subscription(release)
        self._routes.bind(parsed, inbox, granted)
        self.note_grant(inbox, granted)
        return granted

    def subscription_count(self, topic: str, inbox: Inbox) -> int:
        try:
            parts = split_topic(topic)
        except (EnvelopeBuildError, TypeError, AttributeError):
            return 0
        return self._routes.hold_count(parts, inbox)

    def ready_or_watch(self, envelope: Envelope, interest: Interest) -> bool:
        self._routes.changes.watch(envelope.header.topic, interest)
        targets = self._routes.snapshot_match(split_topic(envelope.header.topic))
        ready = True
        for box in targets:
            if not can_enqueue(box, envelope.header.kind):
                watch_space(box, interest)
                ready = False
        return ready
