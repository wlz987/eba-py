from __future__ import annotations

from typing import TYPE_CHECKING

from eba.envelope.envelope import IdGen
from eba.envelope.reply import Matchmaker
from eba.job.context_types import Control
from eba.job.ending import seal_job
from eba.job.job import state_of
from eba.mail.bus import Bus

if TYPE_CHECKING:
    from eba.job.core import Core


def resolve_held(core: Core, bus: Bus, id_gen: IdGen) -> bool:
    progressed = False
    for request_id, reply in list(core.held.items()):
        body = reply._take()
        if body is None:
            continue
        job = core.jobs.get(request_id)
        state = state_of(job) if job is not None else None
        if job is None or state is None or not state.held:
            core.held.pop(request_id, None)
            reply._close()
            continue
        core.held.pop(request_id, None)
        state.held = False
        result = Matchmaker(state.root.header).reply(
            body,
            from_=core.sub.actor_id,
            id_gen=id_gen,
        )
        seal_job(core, job)
        from eba.job.execution_ending import _deliver_ending

        _deliver_ending(core, bus, job, result, Control(body))
        progressed = True
    return progressed


def close_held(core: Core) -> None:
    for reply in core.held.values():
        reply._close()
    core.held.clear()
