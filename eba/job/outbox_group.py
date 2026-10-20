from __future__ import annotations

from collections import deque

from eba.envelope.envelope import Envelope
from eba.mail.bus import Bus
from eba.notify.watch import Interest


def _awaited(bus: Bus, envelope: Envelope) -> bool:
    return bus.waiting(envelope.header.correlation_id)


class _Group:
    def __init__(self, interest: Interest) -> None:
        self.interest = interest
        self.items: deque[Envelope] = deque()
