from __future__ import annotations

from eba.time.numbers import nonnegative_int


class Schedule:
    def __init__(
        self,
        ready: bool = False,
        next_deadline_ms: int | None = None,
        is_quiescent: bool = True,
        *,
        now_ms: int | None = None,
    ) -> None:
        if next_deadline_ms is not None:
            nonnegative_int(next_deadline_ms, "deadline_ms")
        self.ready = ready
        self.next_deadline_ms = next_deadline_ms
        self.is_quiescent = is_quiescent
        self.now_ms = None if now_ms is None else nonnegative_int(now_ms, "clock_ms")

    def wait_ms(self, now_ms: int | None = None) -> int | None:
        if now_ms is None:
            if self.now_ms is None:
                raise RuntimeError("schedule has no observed instant")
            now_ms = self.now_ms
        else:
            nonnegative_int(now_ms, "clock_ms")
        if self.ready:
            return 0
        if self.next_deadline_ms is None:
            return None
        return max(0, self.next_deadline_ms - now_ms)
