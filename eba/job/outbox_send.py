from __future__ import annotations

from eba.envelope.envelope import Envelope
from eba.errors import DeliveryError, MailboxFull, OutboxFull
from eba.job.outbox_group import _awaited, _Group
from eba.mail.bus import Bus
from eba.notify.signal import DELIVERY, Signal
from eba.notify.watch import Interest


class _OutboxSend:
    _candidates: dict[str, None]
    _count: int
    _groups: dict[str, _Group]
    _limit: int
    _signal: Signal

    def _queued(self) -> int:
        raise NotImplementedError

    def send(self, bus: Bus, envelope: Envelope) -> None:
        topic = envelope.header.topic
        group = self._groups.get(topic)
        if group is None:
            try:
                published = bus.publish(envelope)
            except MailboxFull:
                pass
            except Exception as error:
                raise DeliveryError(envelope, "result publication failed") from error
            else:
                if published is False and _awaited(bus, envelope):
                    raise DeliveryError(envelope, "result publication failed")
                return
        if self._queued() >= self._limit:
            raise OutboxFull(envelope)
        first = group is None
        if group is None:
            group = _Group(Interest(self._signal, self._candidates, topic))
            self._groups[topic] = group
        group.items.append(envelope)
        self._count += 1
        if not first:
            return
        try:
            if bus.ready_or_watch(envelope, group.interest):
                self._candidates[topic] = None
                self._signal.notify(DELIVERY)
        except Exception as error:
            group.interest.dispose()
            self._count -= 1
            self._groups.pop(topic, None)
            raise DeliveryError(envelope, "result delivery registration failed") from error
