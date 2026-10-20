from __future__ import annotations

from eba.job.core import Core
from eba.mail.inbox import pause_work
from eba.notify.signal import TIMER, WORK


def _recompute_pause(core: Core) -> None:
    pause_work(core.sub.inbox, _holding(core) and core.queue.full)


def _refresh(core: Core, now_ms: int) -> None:
    holding = _holding(core)
    _recompute_pause(core)
    arm_closed_waits(core)
    core.signal.set(WORK, not holding and core.queue.size > 0)
    deadline = core.book.next_deadline_ms
    core.signal.set(TIMER, deadline is not None and deadline <= now_ms)


def _holding(core: Core) -> bool:
    return core.pending is not None or bool(core.rest)


def arm_closed_waits(core: Core) -> None:
    if core.state not in {"running", "draining"}:
        return
    if not core.sub.inbox.is_closed:
        return
    core.book.elapse_open()
