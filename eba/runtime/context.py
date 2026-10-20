from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from eba.time.clock import Clock

if TYPE_CHECKING:
    from eba.runtime.runtime import Runtime


class _Writing:
    __slots__ = ("_runtime",)

    def __init__(self, runtime: Runtime) -> None:
        self._runtime = runtime

    def __enter__(self) -> None:
        runtime = self._runtime
        if runtime._busy or runtime._reading_clock or runtime._state == "closed":
            raise RuntimeError("closed or reentrant runtime")
        runtime._busy = True

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> Literal[False]:
        self._runtime._busy = False
        return False


class _ClockView(Clock):
    def __init__(self, runtime: Runtime) -> None:
        self._runtime = runtime

    def now_ms(self) -> int:
        return self._runtime._now()
