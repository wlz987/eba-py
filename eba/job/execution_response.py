from __future__ import annotations

from collections.abc import Callable

from eba.envelope.envelope import Envelope, IdGen
from eba.envelope.reply import Matchmaker
from eba.envelope.result import err_payload
from eba.errors import combine_failures
from eba.job.core import Core
from eba.job.delivery import hold_or_send, holds_letter
from eba.job.ending import drop_job, invoke, seal_job
from eba.job.job import Control, Job, State
from eba.mail.bus import Bus


def _observe(action: Callable[[], None], observer: Callable[[], None]) -> None:
    try:
        action()
    except Exception as error:
        try:
            observer()
        except Exception as secondary:
            raise combine_failures(error, secondary)  # noqa: B904  # noqa: B904
        raise
    observer()


def _defer_ending(
    core: Core,
    bus: Bus,
    job: Job,
    state: State,
    control: Control,
    reply: Envelope | None,
    error: Exception,
) -> None:
    state.pending_control = control
    if reply is None:
        return
    try:
        hold_or_send(core, bus, job, reply)
        state.replied = True
    except Exception as delivery_error:
        if holds_letter(core, reply):
            state.replied = True
        raise combine_failures(error, delivery_error)  # noqa: B904


def remove(core: Core, job: Job) -> None:
    seal_job(core, job)
    drop_job(core, job)


def _respond(core: Core, bus: Bus, id_gen: IdGen, root: Envelope, body: object) -> None:
    hold_or_send(
        core,
        bus,
        None,
        Matchmaker(root.header).reply(body, from_=core.sub.actor_id, id_gen=id_gen),
    )


def reject(core: Core, bus: Bus, id_gen: IdGen, root: Envelope, reason: str) -> None:
    core.rejected_count += 1

    def send() -> None:
        if root.header.kind == "request":
            _respond(core, bus, id_gen, root, err_payload(reason))

    def observe() -> None:
        invoke(lambda: core.on_rejected(root, reason))

    _observe(send, observe)
