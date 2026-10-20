from __future__ import annotations

from eba.envelope.envelope import Envelope
from eba.envelope.ids import EnvelopeId
from eba.mail.inbox import Inbox, _state
from eba.notify.signal import READ, Signal
from eba.notify.watch import Interest


def can_enqueue(inbox: Inbox, kind: str) -> bool:
    state = _state(inbox)
    return (
        not state.closed
        and len(state.items) < inbox.capacity
        and (not state.work_paused or kind not in ("event", "request"))
    )


def pause_work(inbox: Inbox, paused: bool) -> None:
    state = _state(inbox)
    if state.work_paused == paused:
        return
    state.work_paused = paused
    if not paused:
        state.space.notify()


def enqueue(inbox: Inbox, envelope: Envelope) -> bool:
    if not can_enqueue(inbox, envelope.header.kind):
        return False
    _state(inbox).items.append(envelope)
    return True


def holds_kind(inbox: Inbox, kind: str) -> bool:
    return any(item.header.kind == kind for item in _state(inbox).items)


def held_count(inbox: Inbox) -> int:
    return len(_state(inbox).items)


def pull_kind(inbox: Inbox, kind: str) -> Envelope | None:
    state = _state(inbox)
    items = state.items
    full = len(items) == inbox.capacity
    for index, item in enumerate(items):
        if item.header.kind != kind:
            continue
        del items[index]
        if not items:
            state.read.clear(READ)
        if full:
            state.space.notify()
        return item
    return None


def find(inbox: Inbox, envelope_id: EnvelopeId) -> Envelope | None:
    for item in _state(inbox).items:
        if item.header.id == envelope_id:
            return item
    return None


def remaining(inbox: Inbox) -> int:
    state = _state(inbox)
    if state.closed:
        return 0
    return inbox.capacity - len(state.items)


def mark_read(inbox: Inbox) -> None:
    _state(inbox).read.notify(READ)


def read_signal(inbox: Inbox) -> Signal:
    return _state(inbox).read


def watch_space(inbox: Inbox, interest: Interest) -> None:
    _state(inbox).space.watch(interest)


def reply_topic(inbox: Inbox) -> str:
    return f"sys.reply.i{inbox.id}"


def take_seized(inbox: Inbox) -> list[Envelope]:
    state = _state(inbox)
    found = list(state.seized)
    state.seized.clear()
    return found


from eba.mail.receiver import Receiver as Receiver  # noqa: E402
