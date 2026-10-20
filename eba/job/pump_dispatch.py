from __future__ import annotations

from eba.envelope.envelope import Envelope, IdGen, checked_envelope
from eba.envelope.errors import EnvelopeBuildError
from eba.job.core import Core
from eba.job.execution import refused
from eba.job.execution_response import reject
from eba.job.resume import keep_unread
from eba.mail.bus import Bus


def _dispatch(core: Core, bus: Bus, id_gen: IdGen, envelope: Envelope) -> None:
    frozen = _snapshot_or_keep(core, envelope)
    if frozen is None:
        return
    if frozen.header.kind == "diagnostic":
        return
    reason = refused(core)
    if reason is None and not core.queue.push(frozen):
        reason = "queue_full"
    if reason is not None:
        reject(core, bus, id_gen, frozen, reason)


def _snapshot_or_keep(core: Core, envelope: Envelope) -> Envelope | None:
    try:
        return checked_envelope(envelope)
    except (EnvelopeBuildError, TypeError, AttributeError):
        keep_unread(core, envelope)
        return None
