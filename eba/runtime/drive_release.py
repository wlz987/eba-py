from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from eba.envelope.envelope import Envelope
from eba.envelope.result import Completion
from eba.errors import MailboxFull
from eba.job.caller import Caller
from eba.mail.inbox import watch_space
from eba.runtime.signals import _SpaceKick

if TYPE_CHECKING:
    from eba.runtime.drive import Drive
    from eba.runtime.runtime import Runtime


class _DriveRelease:
    runtime: Runtime
    _stops: list[tuple[Caller, str]]
    _waiters: dict[tuple[int, str], tuple[Envelope, asyncio.Future[Completion]]]
    _space_kicks: dict[int, _SpaceKick]

    def _retire(self, done: asyncio.Future[None], error: BaseException | None) -> None:
        if done.done():
            return
        if error is None:
            done.set_result(None)
        else:
            done.set_exception(error)

    def _release(self) -> None:
        self._releasing = True
        try:
            kept: list[tuple[Caller, str]] = []
            for caller, root_id in self._stops:
                try:
                    caller.cancel(root_id)
                except MailboxFull:
                    kept.append((caller, root_id))
                    self._arm_space(caller)
                except RuntimeError:
                    if caller.state in {"closing", "closed"} or caller.inbox.is_closed:
                        continue
                    raise
            self._stops = kept
        finally:
            self._releasing = False

    def _arm_space(self, caller: Caller) -> None:
        inbox = caller.inbox
        key = id(inbox)
        if key in self._space_kicks:
            return
        kick = _SpaceKick(cast("Drive", self), inbox)
        self._space_kicks[key] = kick
        watch_space(inbox, kick)

    def _delay(self) -> float | None:
        wait = self.runtime.schedule().wait_ms()
        if wait == 0:
            return 0
        if wait is None or not self.runtime.clock.arms_timer():
            return None
        return wait / 1000

    def _fail_waiters(self, error: BaseException) -> None:
        pending = [future for _envelope, future in self._waiters.values() if not future.done()]
        self._waiters.clear()
        for future in pending:
            future.set_exception(error)
