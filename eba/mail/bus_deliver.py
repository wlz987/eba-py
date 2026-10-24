from __future__ import annotations

from typing import TYPE_CHECKING, cast

from eba.envelope.envelope import Envelope, checked_envelope
from eba.envelope.errors import EnvelopeBuildError
from eba.envelope.topic import split_topic
from eba.errors import MailboxFull
from eba.mail.inbox import (
    Inbox,
    can_enqueue,
    enqueue,
    mark_read,
    read_signal,
    replace_topic,
    watch_space,
)
from eba.mail.routes import _Routes
from eba.notify.signal import Signal
from eba.notify.watch import Interest

if TYPE_CHECKING:
    from eba.mail.bus import Bus


class _Offer(Interest):
    def __init__(self, bus: Bus, envelope: Envelope, home: object) -> None:
        super().__init__(Signal(), {}, envelope.header.topic)
        self._bus = bus
        self._envelope = envelope
        self._home = home

    def notify(self) -> None:
        self._bus._finish_offer(self)


class _BusDeliver:
    _offers: list[_Offer]
    _routes: _Routes

    def publish(self, envelope: Envelope) -> bool | None:
        envelope = checked_envelope(envelope)
        targets = self._routes.snapshot_match(split_topic(envelope.header.topic))
        if not targets:
            return False
        for box in targets:
            if not can_enqueue(box, envelope.header.kind):
                raise MailboxFull("target inbox full")
        for box in targets:
            enqueue(box, envelope)
        for box in targets:
            mark_read(box)
        return True

    def publish_best_effort(self, envelope: Envelope) -> int:
        """Fan out to every target with room; return how many full or closed targets were skipped."""
        envelope = checked_envelope(envelope)
        targets = self._routes.snapshot_match(split_topic(envelope.header.topic))
        ready = [box for box in targets if can_enqueue(box, envelope.header.kind)]
        for box in ready:
            enqueue(box, envelope)
        for box in ready:
            mark_read(box)
        return len(targets) - len(ready)

    def publish_latest(self, envelope: Envelope) -> int:
        """Keep only the newest event of its topic in each target; return skipped targets."""
        envelope = checked_envelope(envelope)
        if envelope.header.kind != "event":
            raise EnvelopeBuildError("publish_latest requires an event")
        targets = self._routes.snapshot_match(split_topic(envelope.header.topic))
        accepted = [box for box in targets if replace_topic(box, envelope)]
        for box in accepted:
            mark_read(box)
        return len(targets) - len(accepted)

    def deliver(self, envelope: Envelope, home: object) -> None:
        held = checked_envelope(envelope)
        if self._place(held, home):
            return
        offer = _Offer(cast("Bus", self), held, home)
        self._offers.append(offer)
        self._arm(offer)

    def _elsewhere(self, inbox: Inbox, home: object) -> bool:
        signal = read_signal(inbox)
        return not signal.bound_to(home) and not inbox.is_closed

    def _targets(self, envelope: Envelope, home: object) -> list[Inbox]:
        parts = split_topic(envelope.header.topic)
        return [box for box in self._routes.snapshot_match(parts) if self._elsewhere(box, home)]

    def _place(self, envelope: Envelope, home: object) -> bool:
        targets = self._targets(envelope, home)
        if not all(can_enqueue(box, envelope.header.kind) for box in targets):
            return False
        for box in targets:
            enqueue(box, envelope)
        for box in targets:
            mark_read(box)
        return True

    def _arm(self, offer: _Offer) -> None:
        for box in self._targets(offer._envelope, offer._home):
            if not can_enqueue(box, offer._envelope.header.kind):
                watch_space(box, offer)

    def _finish_offer(self, offer: _Offer) -> None:
        if not self._place(offer._envelope, offer._home):
            self._arm(offer)
            return
        if offer in self._offers:
            self._offers.remove(offer)
        offer.dispose()
