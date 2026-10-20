from __future__ import annotations

from eba.envelope.envelope import Envelope, IdGen
from eba.envelope.reply import Matchmaker
from eba.envelope.result import err_payload
from eba.errors import combine_failures, note_settled
from eba.job.core import Core
from eba.job.delivery import hold_or_send, holds_letter
from eba.job.ending import invoke
from eba.job.execution_response import remove
from eba.job.job import Job, become, state_of
from eba.mail.bus import Bus
from eba.mail.inbox import reply_topic


def _fail_hook(core: Core, bus: Bus, id_gen: IdGen, job: Job, error: Exception) -> Exception:
    state = state_of(job)
    root = state.root
    become(state, "finished")
    failure = err_payload("job_failed", {"message": str(error)})
    try:
        invoke(lambda: job.on_finished(failure))
    except Exception as hook_error:
        error = combine_failures(error, hook_error)
    finally:
        state.notice = "finished"
    try:
        remove(core, job)
    except Exception as secondary:
        core.begin_close()
        error = combine_failures(error, secondary)
    if root.header.kind == "request" and not state.replied:
        reply_envelope = None
        try:
            reply_envelope = Matchmaker(root.header).reply(
                failure,
                from_=core.sub.actor_id,
                id_gen=id_gen,
            )
            hold_or_send(core, bus, job, reply_envelope)
            state.replied = True
        except Exception as delivery_error:
            if reply_envelope is not None and holds_letter(core, reply_envelope):
                state.replied = True
            error = combine_failures(error, delivery_error)
    return note_settled(error)


def _silence(core: Core, job: Job, id_gen: IdGen) -> Envelope | None:
    state = state_of(job)
    own_reply = state.root.header.reply_to == reply_topic(core.sub.inbox)
    if state.replied or state.root.header.kind != "request" or (own_reply and not core.book.holds(state.root.header.id)):
        return None
    return Matchmaker(state.root.header).reply(
        err_payload("job_silent"),
        from_=core.sub.actor_id,
        id_gen=id_gen,
    )
