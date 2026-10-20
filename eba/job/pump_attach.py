from __future__ import annotations

from eba.errors import Reentrant
from eba.job.core import Core
from eba.job.pump import _refresh
from eba.mail.bus import Bus


def _enter(core: Core, *, closing: bool = False) -> None:
    if not closing:
        if core.state == "closed":
            raise RuntimeError("host closed")
        if core.state == "closing":
            raise RuntimeError("host closing")
    if core.busy:
        raise Reentrant()
    core.busy = True


def attach_core(core: Core, bus: Bus) -> None:
    _enter(core)
    try:
        core.sub.start(bus)
        _refresh(core, 0)
    finally:
        _idle(core)


def _idle(core: Core) -> None:
    core.busy = False
