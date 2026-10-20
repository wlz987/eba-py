from __future__ import annotations

from typing import TYPE_CHECKING, cast

from eba.envelope.envelope import Envelope
from eba.job.close import close_core
from eba.job.host_core import core_of
from eba.job.turn import require
from eba.mail.bus import Bus

if TYPE_CHECKING:
    from eba.job.host import JobHost


class _HostClose:
    def close(self, bus: Bus) -> list[Envelope]:
        core = core_of(cast("JobHost", self))
        if core.signal.is_bound:
            raise RuntimeError("runtime owns host; use Runtime.close")
        abandoned = close_core(core, bus)
        core.abandoned = None
        return abandoned

    def drain(self) -> None:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), owned=True, _sheet=("eba-sheet",))
        if core.state == "running":
            core.state = "draining"

    def begin_close(self) -> None:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), owned=True, _sheet=("eba-sheet",))
        core.begin_close()

    def close_owned(self, bus: Bus) -> None:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), owned=True, _sheet=("eba-sheet",))
        close_core(core, bus)

    def take_abandoned(self) -> list[Envelope]:
        core = core_of(cast("JobHost", self))
        require(cast("JobHost", self), owned=True, _sheet=("eba-sheet",))
        abandoned = list(core.abandoned or [])
        core.abandoned = None
        return abandoned
