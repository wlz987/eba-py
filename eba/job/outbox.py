from __future__ import annotations

from typing import Literal

from eba.envelope.envelope import Envelope
from eba.errors import DeliveryError, MailboxFull
from eba.job.outbox_group import _awaited, _Group
from eba.job.outbox_send import _OutboxSend
from eba.mail.bus import Bus
from eba.notify.signal import DELIVERY, Signal
from eba.time.numbers import positive_int

Step = Literal["idle", "checked", "advanced"]


class Outbox(_OutboxSend):
    def __init__(self, limit: int, signal: Signal) -> None:
        self._limit = positive_int(limit, "outbox_limit")
        self._signal = signal
        self._candidates: dict[str, None] = {}
        self._groups: dict[str, _Group] = {}
        self._buried: list[Envelope] = []
        self._count = 0

    @property
    def size(self) -> int:
        return self._count

    def _queued(self) -> int:
        return self._count - len(self._buried)

    def has_room(self) -> bool:
        return self._queued() < self._limit

    def rearm(self, envelope: Envelope) -> None:
        topic = envelope.header.topic
        group = self._groups.get(topic)
        if group is None or group.items[0] is not envelope:
            return
        self._candidates[topic] = None
        self._signal.notify(DELIVERY)

    def bury(self, envelope: Envelope) -> None:
        topic = envelope.header.topic
        group = self._groups.get(topic)
        if group is None or group.items[0] is not envelope:
            if not self.contains(envelope):
                self._buried.append(envelope)
                self._count += 1
            return
        self._candidates.pop(topic, None)
        group.interest.dispose()
        group.items.popleft()
        self._buried.append(envelope)
        if group.items:
            self._candidates[topic] = None
            self._signal.notify(DELIVERY)
            return
        del self._groups[topic]
        self._signal.set(DELIVERY, bool(self._candidates))

    def contains(self, envelope: Envelope) -> bool:
        if any(item is envelope for item in self._buried):
            return True
        return any(any(item is envelope for item in group.items) for group in self._groups.values())

    def flush_one(self, bus: Bus) -> tuple[Step, Envelope | None]:
        if not self._candidates:
            self._signal.clear(DELIVERY)
            return "idle", None
        topic = next(iter(self._candidates))
        del self._candidates[topic]
        self._signal.set(DELIVERY, bool(self._candidates))
        group = self._groups[topic]
        envelope = group.items[0]
        group.interest.dispose()
        try:
            if not bus.ready_or_watch(envelope, group.interest):
                return "checked", None
            published = bus.publish(envelope)
        except MailboxFull:
            if bus.ready_or_watch(envelope, group.interest):
                self._candidates[topic] = None
                self._signal.notify(DELIVERY)
            return "checked", None
        except Exception as error:
            group.interest.dispose()
            raise DeliveryError(envelope, "result publication failed") from error
        if published is False and _awaited(bus, envelope):
            group.interest.dispose()
            raise DeliveryError(envelope, "result publication failed")
        group.items.popleft()
        self._count -= 1
        if not group.items:
            group.interest.dispose()
            del self._groups[topic]
        else:
            self._candidates[topic] = None
        self._signal.set(DELIVERY, bool(self._candidates))
        return "advanced", envelope

    def drain(self, envelopes: list[Envelope]) -> None:
        for group in self._groups.values():
            group.interest.dispose()
            while group.items:
                envelopes.append(group.items.popleft())
        envelopes.extend(self._buried)
        self._buried.clear()
        self._groups.clear()
        self._candidates.clear()
        self._signal.clear(DELIVERY)
        self._count = 0
