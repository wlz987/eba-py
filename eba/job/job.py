from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from eba.envelope.envelope import Envelope
from eba.envelope.result import Completion
from eba.job.context import Commit as Commit
from eba.job.context import Context as Context
from eba.job.context import Control as Control
from eba.job.context import _states
from eba.job.context import seal_context as seal_context
from eba.job.context import state_of as state_of
from eba.time.numbers import positive_int

Lifecycle = Literal["new", "active", "delivering", "finished"]
Notice = Literal["open", "rejected", "finished"]
_EDGES = frozenset[tuple[Lifecycle, Lifecycle]](
    {
        ("new", "active"),
        ("active", "delivering"),
        ("active", "finished"),
        ("delivering", "finished"),
        ("finished", "finished"),
    }
)


def become(state: State, lifecycle: Lifecycle) -> None:
    if (state.lifecycle, lifecycle) not in _EDGES:
        raise RuntimeError(f"illegal job transition: {state.lifecycle} -> {lifecycle}")
    state.lifecycle = lifecycle


@dataclass
class State:
    root: Envelope
    max_inflight: int
    lifecycle: Lifecycle = "new"
    notice: Notice = "open"
    replied: bool = False
    held: bool = False
    reply_body: Mapping[str, object] | None = None
    pending_control: Control | None = None


class Job:
    def __init__(self, root: Envelope, max_inflight: int = 100) -> None:
        _states[self] = State(root, positive_int(max_inflight, "max_inflight"))

    @property
    def root(self) -> Envelope:
        return state_of(self).root

    @property
    def finished(self) -> bool:
        return state_of(self).lifecycle == "finished"

    def begin(self, _ctx: Context) -> None:
        return None

    def on_stage_result(self, _ctx: Context, _stage: str, _completion: Completion) -> None:
        return None

    def on_finished(self, _body: Mapping[str, object] | None) -> None:
        return None
