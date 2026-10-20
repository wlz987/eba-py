from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from eba.errors import DeliveryError, is_settled
from eba.runtime.drive_release import _DriveRelease
from eba.runtime.signals import _Signal

if TYPE_CHECKING:
    from eba.runtime.runtime import Runtime


class _DriveRun(_DriveRelease):
    runtime: Runtime
    _closed: bool
    _pumping: bool
    _releasing: bool
    _wake: _Signal

    async def _run(self, done: asyncio.Future[None]) -> None:
        try:
            while not self._closed:
                self._release()
                try:
                    self._pumping = True
                    try:
                        moved = self.runtime.advance()
                    finally:
                        self._pumping = False
                except Exception as error:
                    if isinstance(error, DeliveryError) or is_settled(error):
                        moved = True
                    else:
                        raise
                delay = self._delay()
                if delay == 0 and moved:
                    await asyncio.sleep(0)
                    continue
                if delay == 0:
                    delay = None
                wake = self._wake
                if wake.consume():
                    continue
                loop = asyncio.get_running_loop()
                waiter = loop.create_future()
                alarm = None if delay is None else loop.call_later(delay, wake.expire, waiter)
                wake.arm(waiter)
                try:
                    await waiter
                finally:
                    wake.disarm(waiter)
                    if alarm is not None:
                        alarm.cancel()
            self._release()
        except asyncio.CancelledError:
            self._fail_waiters(RuntimeError("drive cancelled"))
            raise
        except Exception as error:
            self._fail_waiters(error)
            self._retire(done, error)
            raise
        finally:
            self._retire(done, None)
