import time

from eba.errors import ClockError
from eba.time.numbers import nonnegative_int


class Clock:
    def now_ms(self) -> int:
        raise NotImplementedError("now_ms")

    def arms_timer(self) -> bool:
        return True


def read_clock(clock: Clock) -> int:
    try:
        return nonnegative_int(clock.now_ms(), "clock_ms")
    except ClockError:
        raise
    except Exception as error:
        raise ClockError(str(error)) from error


class _Pinned(Clock):
    def __init__(self, now_ms: int) -> None:
        self._now_ms = now_ms

    def now_ms(self) -> int:
        return self._now_ms


def pin_clock(now_ms: int) -> Clock:
    return _Pinned(now_ms)


class MonotonicClock(Clock):
    def now_ms(self) -> int:
        return time.monotonic_ns() // 1_000_000


class ManualClock(Clock):
    def __init__(self, now_ms: int = 0) -> None:
        self._now = nonnegative_int(now_ms, "now_ms")

    def now_ms(self) -> int:
        return self._now

    def arms_timer(self) -> bool:
        return False

    def advance(self, ms: int) -> None:
        step = nonnegative_int(ms, "advance_ms")
        self._now += step
