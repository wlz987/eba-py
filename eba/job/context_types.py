from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from eba.envelope.envelope import Envelope, IdGen
from eba.envelope.ids import ActorId

if TYPE_CHECKING:
    from eba.job.job import State


@dataclass
class _Intent:
    stage: str
    request: Envelope
    timeout: int | None = None


@dataclass
class Control:
    body: Mapping[str, object] | None


class _Buffer:
    def __init__(
        self,
        job: State,
        actor_id: ActorId,
        reply_to: str,
        id_gen: IdGen | None,
        pending_count: int,
    ) -> None:
        self.job = job
        self.actor_id = actor_id
        self.reply_to = reply_to
        self.id_gen = id_gen
        self.pending_count = pending_count
        self.busy = False
        self.requests: list[_Intent] = []
        self.reply: Mapping[str, object] | None = None
        self.control: Control | None = None
