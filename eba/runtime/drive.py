from __future__ import annotations

import asyncio
import weakref
from types import TracebackType

from eba.envelope.envelope import Envelope
from eba.envelope.result import Completion
from eba.job.caller import Caller
from eba.runtime.drive_open import _DriveOpen
from eba.runtime.drive_run import _DriveRun
from eba.runtime.runtime import Runtime
from eba.runtime.signals import Pending as Pending
from eba.runtime.signals import _Signal, _SpaceKick

_attached: weakref.WeakKeyDictionary[Runtime, Drive] = weakref.WeakKeyDictionary()


class Drive(_DriveOpen, _DriveRun):
    _waiters: dict[tuple[int, str], tuple[Envelope, asyncio.Future[Completion]]]
    _stops: list[tuple[Caller, str]]
    _space_kicks: dict[int, _SpaceKick]
    _wake: _Signal
    _closed: bool
    _pumping: bool
    _releasing: bool

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime
        self._task: asyncio.Task[None] | None = None
        self._done: asyncio.Future[None] | None = None
        self._reset()

    def _reset(self) -> None:
        self._waiters = {}
        self._stops = []
        self._space_kicks = {}
        self._wake = _Signal()
        self._closed = False
        self._pumping = False
        self._releasing = False

    async def __aenter__(self) -> Drive:
        if self._done is not None and not self._done.done():
            raise RuntimeError("drive already running")
        prior = _attached.get(self.runtime)
        if prior is not None and prior is not self and prior._done is not None and not prior._done.done():
            raise RuntimeError("runtime already has a drive")
        self._reset()
        done = asyncio.get_running_loop().create_future()
        self._done = done
        self.runtime.bind_wake(self.kick)
        self._task = asyncio.get_running_loop().create_task(self._run(done))
        _attached[self.runtime] = self
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._closed = True
        self.kick()
        done = self._done
        self.runtime.bind_wake(None)
        if _attached.get(self.runtime) is self:
            _attached.pop(self.runtime, None)
        try:
            if done is not None:
                await done
        finally:
            task = self._task
            self._task = None
            self._done = None
            if task is not None and task.done():
                try:  # noqa: SIM105
                    task.exception()
                except asyncio.CancelledError:
                    pass
            self._fail_waiters(RuntimeError("drive closed"))

    def kick(self) -> None:
        if self._pumping or self._releasing:
            return
        self._wake.fire()
