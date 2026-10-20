from __future__ import annotations

from eba.envelope.envelope import IdGen
from eba.job.core import Core
from eba.job.delivery import (
    retry_due,
)
from eba.job.ending import release_deferred, waits_for_lease
from eba.job.pump_ops import _recv as _recv
from eba.job.pump_ops import has_work as has_work
from eba.job.pump_refresh import _holding as _holding
from eba.job.pump_refresh import _recompute_pause as _recompute_pause
from eba.job.pump_refresh import _refresh as _refresh
from eba.job.pump_refresh import arm_closed_waits as arm_closed_waits
from eba.mail.bus import Bus
from eba.mail.inbox import holds_kind
from eba.notify.signal import DELIVERY, READ, TIMER, WORK
from eba.time.clock import Clock, pin_clock, read_clock

_PHASE_FLAG = (READ, TIMER, WORK, DELIVERY)
_SIGNAL_MASK = READ | TIMER | WORK | DELIVERY


def scheduled(core: Core) -> bool:
    if waits_for_lease(core) or retry_due(core) or core.book.unreleased > 0:
        return True
    if not _holding(core):
        return core.signal.has(_SIGNAL_MASK)
    if core.queue.full:
        if holds_kind(core.sub.inbox, "result"):
            return True
        return core.signal.has(TIMER | DELIVERY)
    return core.signal.has(READ | TIMER | DELIVERY)


def advance_host(core: Core, bus: Bus, clock: Clock, id_gen: IdGen) -> bool:
    now = read_clock(clock)
    _enter(core)
    try:
        released = release_deferred(core)
        progressed = _pump(core, bus, pin_clock(now), id_gen, core.work_budget)
        held = core.book.unreleased
        core.book.recover()
        return progressed or released or core.book.unreleased < held
    finally:
        _idle(core)
        _refresh(core, now)


from eba.job.pump_attach import _enter as _enter  # noqa: E402
from eba.job.pump_attach import _idle as _idle  # noqa: E402
from eba.job.pump_attach import attach_core as attach_core  # noqa: E402
from eba.job.pump_dispatch import _dispatch as _dispatch  # noqa: E402
from eba.job.pump_dispatch import _snapshot_or_keep as _snapshot_or_keep  # noqa: E402
from eba.job.pump_step import _pump  # noqa: E402
