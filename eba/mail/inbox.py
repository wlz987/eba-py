from __future__ import annotations

from eba.mail.inbox_state import _TOKEN as _TOKEN
from eba.mail.inbox_state import _RouteOwner as _RouteOwner
from eba.mail.inbox_state import _State as _State
from eba.mail.inbox_state import _state as _state
from eba.mail.inbox_state import _states as _states
from eba.notify.signal import READ
from eba.time.numbers import positive_int

_next_id = 0
_closes = 0


def close_count() -> int:
    return _closes


def note_close() -> None:
    global _closes
    _closes += 1


class Inbox:
    __slots__ = ("__weakref__", "capacity", "id")

    def __init__(self, capacity: int) -> None:
        global _next_id
        _next_id += 1
        self.id = _next_id
        self.capacity = positive_int(capacity, "capacity")
        _states[self] = _State()

    def receiver(self) -> Receiver:
        return Receiver._claim(self)

    @property
    def is_closed(self) -> bool:
        return _state(self).closed

    @property
    def has_read(self) -> bool:
        return _state(self).read.has(READ)

    def remaining(self) -> int:
        return remaining(self)


def remember_route(inbox: Inbox, owner: _RouteOwner) -> None:
    _state(inbox).routes.add(owner)


def forget_route(inbox: Inbox, owner: _RouteOwner) -> None:
    _state(inbox).routes.discard(owner)


from eba.mail.inbox_ops import (  # noqa: E402  # noqa: E402
    can_enqueue as can_enqueue,
)
from eba.mail.inbox_ops import (  # noqa: E402
    enqueue as enqueue,
)
from eba.mail.inbox_ops import (  # noqa: E402
    find as find,
)
from eba.mail.inbox_ops import (  # noqa: E402
    held_count as held_count,
)
from eba.mail.inbox_ops import (  # noqa: E402
    holds_kind as holds_kind,
)
from eba.mail.inbox_ops import (  # noqa: E402
    mark_read as mark_read,
)
from eba.mail.inbox_ops import (  # noqa: E402
    pause_work as pause_work,
)
from eba.mail.inbox_ops import (  # noqa: E402
    pull_kind as pull_kind,
)
from eba.mail.inbox_ops import (  # noqa: E402
    read_signal as read_signal,
)
from eba.mail.inbox_ops import (  # noqa: E402
    remaining as remaining,
)
from eba.mail.inbox_ops import (  # noqa: E402
    remove as remove,
)
from eba.mail.inbox_ops import (  # noqa: E402
    replace_topic as replace_topic,
)
from eba.mail.inbox_ops import (  # noqa: E402
    reply_topic as reply_topic,
)
from eba.mail.inbox_ops import (  # noqa: E402
    take_seized as take_seized,
)
from eba.mail.inbox_ops import (  # noqa: E402
    watch_space as watch_space,
)
from eba.mail.receiver import Receiver as Receiver  # noqa: E402
