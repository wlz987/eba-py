from __future__ import annotations

import weakref
from collections.abc import Mapping
from typing import TYPE_CHECKING

from eba.job.context_types import Control, _Intent

if TYPE_CHECKING:
    from eba.job.job import Job, State
    from eba.job.reply import Reply

_states: weakref.WeakKeyDictionary[Job, State] = weakref.WeakKeyDictionary()


def state_of(job: Job) -> State:
    try:
        return _states[job]
    except KeyError as error:
        raise RuntimeError("Job constructor must run") from error


class Commit:
    def __init__(
        self,
        requests: list[_Intent],
        reply: Mapping[str, object] | None,
        control: Control | None,
        hold: Reply | None = None,
    ) -> None:
        self.requests = requests
        self.reply = reply
        self.control = control
        self.hold = hold
