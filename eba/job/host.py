from __future__ import annotations

import weakref

from eba.envelope.envelope import Envelope
from eba.envelope.ids import ActorId
from eba.job.core import Core
from eba.job.host_close import _HostClose
from eba.job.host_core import _cores
from eba.job.host_ops import _HostOps
from eba.job.host_view import _HostView
from eba.job.job import Job
from eba.job.turn import require
from eba.mail.inbox import Receiver


class JobHost(_HostClose, _HostOps, _HostView):
    def __init__(
        self,
        *,
        actor_id: ActorId | str,
        receiver: Receiver,
        patterns: list[str] | tuple[str, ...],
        request_timeout_ms: int | None = None,
        queue_limit: int = 512,
        active_limit: int = 256,
        work_budget: int = 64,
        outbox_limit: int = 512,
    ) -> None:
        host = weakref.ref(self)

        def make_job(root: Envelope) -> Job:
            found = host()
            if found is None:
                raise RuntimeError("invalid JobHost")
            return found.make_job(root)

        def on_rejected(root: Envelope, reason: str) -> None:
            found = host()
            if found is None:
                return None
            return found.on_rejected(root, reason)

        _cores[self] = Core(
            actor_id=actor_id,
            receiver=receiver,
            patterns=patterns,
            request_timeout_ms=request_timeout_ms,
            queue_limit=queue_limit,
            active_limit=active_limit,
            work_budget=work_budget,
            outbox_limit=outbox_limit,
            make_job=make_job,
            on_rejected=on_rejected,
        )
        require(self, op="born", _sheet=("eba-sheet",))


def _born() -> None:
    from eba.job.turn import install_roster

    install_roster()
    import eba.job.turn as turn

    del turn.install_roster


_born()
del _born
