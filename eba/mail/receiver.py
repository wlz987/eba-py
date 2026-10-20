from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from eba.envelope.envelope import Envelope
from eba.mail.inbox import _TOKEN, _state, note_close
from eba.notify.signal import READ

if TYPE_CHECKING:
    from eba.mail.inbox import Inbox


class Receiver:
    __slots__ = ("_active", "_borrows", "inbox")

    def __init__(self, inbox: Inbox, token: object) -> None:
        if token is not _TOKEN:
            raise RuntimeError("use Inbox.receiver()")
        self.inbox = inbox
        self._active = True
        self._borrows = 0

    @staticmethod
    def _claim(inbox: Inbox) -> Receiver:
        state = _state(inbox)
        if state.closed or state.claimed:
            raise RuntimeError("inbox unavailable or already owned")
        state.claimed = True
        return Receiver(inbox, _TOKEN)

    @property
    def is_active(self) -> bool:
        return self._active

    def borrow(self) -> Callable[[], None]:
        self._require_active()
        self._borrows += 1
        released = False

        def release() -> None:
            nonlocal released
            if not released:
                self._borrows -= 1
                released = True

        return release

    def take(self) -> Receiver:
        self._require_active()
        if self._borrows:
            raise RuntimeError("receiver is borrowed")
        transferred = Receiver(self.inbox, _TOKEN)
        self._active = False
        return transferred

    def try_recv(self) -> Envelope | None:
        self._require_active()
        state = _state(self.inbox)
        full = len(state.items) == self.inbox.capacity
        envelope = state.items.popleft() if state.items else None
        if not state.items:
            state.read.clear(READ)
        if envelope is not None and full:
            state.space.notify()
        return envelope

    def close(self) -> bool:
        state = _state(self.inbox)
        started = self._active
        if started:
            global _closes
            self._active = False
            state.closed = True
            note_close()
            if state.items:
                state.seized.extend(state.items)
                state.items.clear()
            state.read.clear(READ)
            state.space.notify()
        elif not state.closed:
            return False
        for owner in list(state.routes):
            try:
                owner.unsubscribe_all(self.inbox)
            finally:
                state.routes.discard(owner)
        return started

    def _require_active(self) -> None:
        if not self._active:
            raise RuntimeError("receiver transferred or closed")
