from __future__ import annotations

from eba.envelope.envelope import Envelope
from eba.envelope.ids import ActorId, actor_id
from eba.errors import combine_failures
from eba.mail.bus import Bus, Subscription
from eba.mail.inbox import Inbox, Receiver
from eba.pattern import parse_pattern

_UNSET = object()
_CHANGING = object()


class Subscriber:
    def __init__(self, actor: ActorId | str, receiver: Receiver, patterns: tuple[str, ...] | list[str] = ()) -> None:
        self.actor_id = actor_id(actor)
        self.patterns = tuple(patterns)
        for pattern in self.patterns:
            parse_pattern(pattern)
        self.receiver = receiver.take()
        self.inbox: Inbox = self.receiver.inbox
        self._subscriptions: object = _UNSET
        self._owed: list[Subscription] = []

    def start(self, bus: Bus) -> None:
        if self._subscriptions is not _UNSET:
            if self._subscriptions is _CHANGING:
                raise RuntimeError("reentrant subscriber mutation")
            raise RuntimeError("subscriber already started")
        if self.inbox.is_closed:
            raise RuntimeError("inbox closed")
        release_receiver = self.receiver.borrow()
        subscriptions: list[Subscription] = []
        self._subscriptions = _CHANGING
        try:
            _release(self._owed)
            for pattern in self.patterns:
                subscriptions.append(bus.subscribe(pattern, self.inbox))  # noqa: PERF401
            if self.inbox.is_closed:
                raise RuntimeError("inbox closed")
            self._subscriptions = subscriptions
        except Exception as error:
            try:
                _release(subscriptions)
            except Exception as secondary:
                self._owed.extend(subscriptions)
                raise combine_failures(error, secondary)  # noqa: B904
            raise
        finally:
            release_receiver()
            if self._subscriptions is _CHANGING:
                self._subscriptions = _UNSET

    def stop(self) -> None:
        self._release()

    def close(self, bus: Bus) -> None:
        self._release(bus)

    def try_recv(self) -> Envelope | None:
        return self.receiver.try_recv()

    def _release(self, bus: Bus | None = None) -> None:
        if self._subscriptions is _CHANGING:
            raise RuntimeError("reentrant subscriber mutation")
        subscriptions = self._subscriptions if isinstance(self._subscriptions, list) else None
        self._subscriptions = _CHANGING
        try:
            if subscriptions is not None:
                _release(subscriptions)
            _release(self._owed)
            if bus is not None:
                self.receiver.close()
        finally:
            self._subscriptions = subscriptions or _UNSET


def _release(subscriptions: list[Subscription]) -> None:
    while subscriptions:
        subscriptions[-1].close()
        subscriptions.pop()
