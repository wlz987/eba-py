from __future__ import annotations

from collections.abc import Mapping

from eba.envelope.envelope import Envelope, IdGen
from eba.envelope.reply import Matchmaker
from eba.errors import DeliveryError
from eba.job.core import Core
from eba.job.delivery import hold_or_send
from eba.job.ending import leave_ending, settle_ending
from eba.job.execution import _deadline
from eba.job.execution_hook import _fail_hook as _fail_hook
from eba.job.execution_hook import _silence as _silence
from eba.job.job import Commit, Control, Job, state_of
from eba.mail.bus import Bus
from eba.time.clock import Clock


def _prepare_ending(
    core: Core,
    bus: Bus,
    clock: Clock,
    id_gen: IdGen,
    job: Job,
    commit: Commit,
) -> tuple[Envelope | None, Control | None]:
    if commit.hold is not None:
        return None, None
    reply, control = _commit(core, bus, clock, id_gen, job, commit)
    if control is None:
        return reply, None
    if reply is None:
        reply = _silence(core, job, id_gen)
        if reply is not None and isinstance(reply.payload, Mapping):
            control = Control(reply.payload)
    return reply, control


def _deliver_ending(
    core: Core,
    bus: Bus,
    job: Job,
    reply: Envelope | None,
    control: Control | None,
) -> None:
    state = state_of(job)
    if reply is not None:
        try:
            accepted = hold_or_send(core, bus, job, reply)
        except DeliveryError:
            state.replied = True
            leave_ending(job, control)
            raise
        state.replied = True
        if not accepted:
            leave_ending(job, control)
            return
    settle_ending(core, job, control)


def _commit(
    core: Core,
    bus: Bus,
    clock: Clock,
    id_gen: IdGen,
    job: Job,
    commit: Commit,
) -> tuple[Envelope | None, Control | None]:
    root = state_of(job).root
    state = state_of(job)
    reply = None
    if commit.reply is not None:
        reply = Matchmaker(root.header).reply(commit.reply, from_=core.sub.actor_id, id_gen=id_gen)
        state.reply_body = commit.reply
    control = commit.control
    if control is None:
        for intent in commit.requests:
            core.book.submit(
                bus,
                core.sub.inbox,
                intent.request,
                root.header.id,
                intent.stage,
                _deadline(core, clock, intent.timeout),
            )
        if core.book.count(root.header.id) == 0:
            control = Control(state.reply_body)
    elif control.body is None:
        control = Control(state.reply_body)
    return reply, control
