from __future__ import annotations

from collections.abc import Callable

from eba.envelope.envelope import IdGen
from eba.errors import note_settled
from eba.job.core import Core
from eba.job.ending import invoke, seal_job
from eba.job.execution_response import _defer_ending
from eba.job.job import Context, Control, Job, seal_context, state_of
from eba.mail.bus import Bus
from eba.mail.inbox import reply_topic
from eba.time.clock import Clock, read_clock
from eba.time.numbers import nonnegative_int


def refused(core: Core) -> str | None:
    if core.state != "running":
        return "host_draining"
    return None


def _deadline(core: Core, clock: Clock, timeout: int | None = None) -> int | None:
    chosen = core.timeout if timeout is None else timeout
    if chosen is None:
        return None
    now = read_clock(clock)
    return nonnegative_int(now + chosen, "deadline_ms")


def run_hook(core: Core, bus: Bus, clock: Clock, id_gen: IdGen, job: Job, callback: Callable[[Context], object]) -> None:
    state = state_of(job)
    root = state.root
    ctx = Context(
        job,
        actor_id=core.sub.actor_id,
        reply_to=reply_topic(core.sub.inbox),
        id_gen=id_gen,
        pending_count=core.book.count(root.header.id),
        core=core,
        bus=bus,
    )
    control: Control | None = None
    try:
        try:
            invoke(lambda: callback(ctx))
        finally:
            commit = seal_context(ctx)
        reply, control = _prepare_ending(core, bus, clock, id_gen, job, commit)
        if commit.hold is not None:
            return
        if control is not None:
            seal_job(core, job)
    except Exception as error:
        if control is None:
            raise _fail_hook(core, bus, id_gen, job, error)  # noqa: B904
        if core.state == "running":
            note_settled(error)
        _defer_ending(core, bus, job, state, control, reply, error)
        raise
    _deliver_ending(core, bus, job, reply, control)


from eba.job.execution_ending import (  # noqa: E402
    _deliver_ending,
    _fail_hook,
    _prepare_ending,
)
