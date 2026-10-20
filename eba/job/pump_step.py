from __future__ import annotations

from eba.envelope.envelope import Envelope, IdGen
from eba.errors import DeliveryError
from eba.job.core import Core
from eba.job.delivery import (
    note_delivery_success,
    raise_delivery_failure,
    release_result,
    retry_due,
)
from eba.job.execution import refused
from eba.job.execution_response import reject
from eba.job.outbox import Step
from eba.job.pump import (
    _PHASE_FLAG,
    _dispatch,
    _holding,
    _recv,
    _refresh,
    _snapshot_or_keep,
)
from eba.job.resume import adopt, resume
from eba.mail.bus import Bus
from eba.mail.inbox import pull_kind
from eba.notify.signal import DELIVERY
from eba.time.clock import Clock, read_clock


def _step(core: Core, bus: Bus, clock: Clock, id_gen: IdGen, phase: int) -> Step:
    if _holding(core) and phase == 2:
        return "idle"
    if _holding(core) and phase == 0:
        envelope = pull_kind(core.sub.inbox, "result")
        if envelope is not None:
            resume(core, bus, clock, id_gen, envelope)
            return "advanced"
        if core.queue.full:
            return "idle"
        envelope = _recv(core)
        if envelope is None:
            return "idle"
        frozen = _snapshot_or_keep(core, envelope)
        if frozen is None or frozen.header.kind == "diagnostic":
            return "advanced"
        core.queue.push(frozen)
        return "advanced"
    if phase == 3 and (retry_due(core) or core.signal.has(DELIVERY)):
        try:
            step, sent = core.outbox.flush_one(bus)
        except DeliveryError as error:
            raise_delivery_failure(core, error)
        if sent is not None:
            note_delivery_success(core, sent)
        if release_result(core, bus) and step == "idle":
            step = "advanced"
        return step
    if not core.signal.has(_PHASE_FLAG[phase]):
        return "idle"
    if phase == 0:
        envelope = _recv(core)
        if envelope is None:
            return "idle"
        if envelope.header.kind == "result":
            resume(core, bus, clock, id_gen, envelope)
        else:
            _dispatch(core, bus, id_gen, envelope)
        return "advanced"
    if phase == 1:
        resume(core, bus, clock, id_gen, read_clock(clock))
        return "advanced"
    root = core.queue.shift()
    if not isinstance(root, Envelope):
        return "idle"
    reason = refused(core)
    if reason is None and len(core.jobs) >= core.active_limit:
        reason = "active_full"
    if reason is not None:
        reject(core, bus, id_gen, root, reason)
    else:
        adopt(core, bus, clock, id_gen, root)
    return "advanced"


def _pump(core: Core, bus: Bus, clock: Clock, id_gen: IdGen, budget: int) -> bool:
    progressed = False
    idle = 0
    while budget > 0 and idle < 4:
        phase = core.phase
        core.phase = (phase + 1) % 4
        now = read_clock(clock)
        try:
            advanced = _step(core, bus, clock, id_gen, phase)
        finally:
            _refresh(core, now)
        if advanced == "idle":
            idle += 1
            continue
        budget -= 1
        progressed = progressed or advanced == "advanced"
        idle = 0
    return progressed
