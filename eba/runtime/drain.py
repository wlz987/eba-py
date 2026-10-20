from __future__ import annotations

import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING

from eba.envelope.ids import ActorId
from eba.job.host import JobHost

if TYPE_CHECKING:
    pass

_DENIED = "runtime is the only writer"


class _RuntimeDrain:
    _state: str
    _reading_clock: bool
    _busy: bool
    _select: Callable[[ActorId | str | None], list[JobHost]]
    _enter: Callable[[], AbstractContextManager[None]]

    def shutdown(self, actor_id: ActorId | str | None = None) -> None:
        if self._state in {"closed", "closing"}:
            return
        if self._reading_clock:
            raise RuntimeError("reentrant clock observation")
        selected = self._select(actor_id)
        if self._busy:
            self._drain(selected, actor_id)
            return
        with self._enter():
            self._drain(selected, actor_id)

    def _drain(self, selected: list[JobHost], actor_id: ActorId | str | None) -> None:
        if sys._getframe(1).f_code is not self.shutdown.__code__:
            raise RuntimeError(_DENIED)
        if actor_id is None:
            self._state = "draining"
        for host in selected:
            JobHost.drain(host)
