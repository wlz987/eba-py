from __future__ import annotations

from eba.envelope.envelope import Envelope
from eba.errors import LeasePending, combine_failures
from eba.job.core import Core
from eba.job.ending import invoke, release_ending
from eba.job.job import state_of


def _combine_all(errors: list[Exception]) -> Exception:
    chosen = errors[0]
    for secondary in errors[1:]:
        chosen = combine_failures(chosen, secondary)
    return chosen


def _finish_jobs(core: Core, abandoned: list[Envelope]) -> tuple[Exception | None, Exception | None]:
    failures: list[Exception] = []
    for job in list(core.jobs.values()):
        state = state_of(job)
        root = state.root
        if state.pending_control is None and state.notice == "open":
            try:
                invoke(lambda: core.on_rejected(root, "host_draining"))  # noqa: B023
            except Exception as error:
                failures.append(error)
            state.notice = "rejected"
        try:
            release_ending(core, job)
        except LeasePending as error:
            return (_combine_all(failures) if failures else None, error)
        except Exception as error:
            if core.jobs.get(root.header.id) is not job:
                abandoned.append(root)
            failures.append(error)
        else:
            abandoned.append(root)
    return (_combine_all(failures) if failures else None, None)


def _settle_letter(core: Core, envelope: Envelope, abandoned: list[Envelope], *, notify: bool) -> None:
    abandoned.append(envelope)
    if not notify:
        return
    invoke(lambda: core.on_rejected(envelope, "host_draining"))


def _settle_inbound(core: Core, abandoned: list[Envelope], notice: int) -> None:
    while (item := core.queue.shift()) is not None:
        if isinstance(item, Envelope):
            _settle_letter(core, item, abandoned, notify=True)
            notice -= 1
    if core.sub.inbox.is_closed:
        return
    while True:
        envelope = core.sub.try_recv()
        if envelope is None:
            return
        _settle_letter(core, envelope, abandoned, notify=notice > 0)
        notice -= 1
