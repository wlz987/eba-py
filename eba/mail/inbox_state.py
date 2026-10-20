from __future__ import annotations

import weakref
from collections import deque
from typing import TYPE_CHECKING, Protocol

from eba.envelope.envelope import Envelope
from eba.notify.signal import Signal
from eba.notify.watch import Watchers

if TYPE_CHECKING:
    from eba.mail.inbox import Inbox

_TOKEN = object()


class _RouteOwner(Protocol):
    def unsubscribe_all(self, inbox: Inbox) -> None:
        pass


class _State:
    __slots__ = ("claimed", "closed", "items", "read", "routes", "seized", "space", "work_paused")

    def __init__(self) -> None:
        self.items: deque[Envelope] = deque()
        self.seized: list[Envelope] = []
        self.closed = False
        self.claimed = False
        self.work_paused = False
        self.read = Signal()
        self.space = Watchers()
        self.routes: weakref.WeakSet[_RouteOwner] = weakref.WeakSet()


_states: weakref.WeakKeyDictionary[Inbox, _State] = weakref.WeakKeyDictionary()


def _state(inbox: Inbox) -> _State:
    try:
        return _states[inbox]
    except KeyError as error:
        raise RuntimeError("invalid Inbox") from error
