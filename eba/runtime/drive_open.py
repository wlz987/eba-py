from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from eba.envelope.envelope import Envelope
from eba.envelope.ids import ActorId
from eba.envelope.result import Completion
from eba.job.caller import Caller
from eba.runtime.signals import Pending, _pay

if TYPE_CHECKING:
    from eba.runtime.runtime import Runtime


class _DriveOpen:
    runtime: Runtime
    _waiters: dict[tuple[int, str], tuple[Envelope, asyncio.Future[Completion]]]
    _stops: list[tuple[Caller, str]]
    _wake: object
    _closed: bool
    _done: asyncio.Future[None] | None

    def kick(self) -> None:
        raise NotImplementedError

    def open(
        self,
        caller: Caller,
        *,
        topic: str,
        payload: object,
        from_: ActorId | str,
        timeout_ms: int | None = None,
    ) -> Pending:
        self._require_running()
        if caller.admitted:
            if not self.runtime.owns(caller):
                raise RuntimeError("caller belongs to another runtime")
        else:
            self.runtime.add(caller)
        future: asyncio.Future[Completion] = asyncio.get_running_loop().create_future()
        envelope = caller.admit(
            topic=topic,
            payload=payload,
            from_=from_,
            timeout_ms=timeout_ms,
            pay=_pay(future),
        )
        self._watch(caller, envelope, future)
        return Pending(envelope, future)

    def _watch(self, caller: Caller, envelope: Envelope, future: asyncio.Future[Completion]) -> None:
        key = (id(caller), str(envelope.header.id))
        self._waiters[key] = (envelope, future)

        def drop(done: asyncio.Future[Completion], key: tuple[int, str] = key) -> None:
            self._waiters.pop(key, None)
            if done.cancelled():
                self._stops.append((caller, key[1]))
                self.kick()

        future.add_done_callback(drop)

    def _require_running(self) -> None:
        if self._closed or self._done is None or self._done.done():
            raise RuntimeError("drive is not running")
