from __future__ import annotations

import inspect

from eba.envelope.envelope import Envelope, IdGen
from eba.errors import combine_failures
from eba.job.book import Continuation
from eba.job.core import Core
from eba.job.execution import run_hook
from eba.job.execution_response import reject
from eba.job.job import Job, become, state_of
from eba.mail.bus import Bus
from eba.rendezvous.records_take import UnreadableResult
from eba.time.clock import Clock


def adopt(core: Core, bus: Bus, clock: Clock, id_gen: IdGen, root: Envelope) -> None:
    if root.header.id in core.jobs:
        reject(core, bus, id_gen, root, "adoption_failed")
        return
    try:
        produced = core.make_job(root)
        if inspect.iscoroutine(produced):
            produced.close()
            raise TypeError("make_job must be synchronous and return a fresh Job")
        job = produced
        if not isinstance(job, Job):
            raise TypeError("make_job must be synchronous and return a fresh Job")
        state = state_of(job)
        if state.root is not root or state.lifecycle != "new":
            raise RuntimeError("factory must return a fresh Job for this root")
    except Exception as error:
        try:
            reject(core, bus, id_gen, root, "adoption_failed")
        except Exception as secondary:
            raise combine_failures(error, secondary)  # noqa: B904
        raise
    become(state_of(job), "active")
    core.jobs[root.header.id] = job
    run_hook(core, bus, clock, id_gen, job, job.begin)


def keep_unread(core: Core, envelope: Envelope) -> None:
    if core.abandoned is None:
        core.abandoned = []
    core.abandoned.append(envelope)


def resume(core: Core, bus: Bus, clock: Clock, id_gen: IdGen, source: Envelope | int) -> None:
    try:
        claim = core.book.take_due(source) if isinstance(source, int) else core.book.take_result(source)
    except UnreadableResult:
        if not isinstance(source, int):
            keep_unread(core, source)
        return
    except Exception:
        abandoned = core.begin_close()
        if not isinstance(source, int):
            abandoned.append(source)
        raise
    if claim is None:
        return
    continuation = claim.continuation
    if not isinstance(continuation, Continuation):
        return
    job = core.jobs.get(continuation.owner)
    if job is None:
        return
    run_hook(
        core,
        bus,
        clock,
        id_gen,
        job,
        lambda ctx: job.on_stage_result(ctx, continuation.stage, claim.completion),
    )
