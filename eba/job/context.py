from __future__ import annotations

from typing import TYPE_CHECKING

from eba.envelope.envelope import Envelope, IdGen
from eba.envelope.ids import ActorId, EnvelopeId
from eba.job.context_buffer import _buffer_of as _buffer_of
from eba.job.context_buffer import _buffers as _buffers
from eba.job.context_buffer import _put_reply as _put_reply
from eba.job.context_buffer import _require_active as _require_active
from eba.job.context_buffer import seal_context as seal_context
from eba.job.context_state import Commit as Commit
from eba.job.context_state import _states as _states
from eba.job.context_state import state_of as state_of
from eba.job.context_types import Control as Control
from eba.job.context_types import _Buffer as _Buffer
from eba.job.context_types import _Intent as _Intent

if TYPE_CHECKING:
    from eba.job.core import Core
    from eba.job.job import Job
    from eba.job.reply import Reply
    from eba.mail.bus import Bus


class Context:
    def __init__(
        self,
        job: Job,
        *,
        actor_id: ActorId,
        reply_to: str,
        id_gen: IdGen,
        pending_count: int,
        core: Core,
        bus: Bus,
    ) -> None:
        _buffers[self] = _Buffer(job, state_of(job), actor_id, reply_to, id_gen, pending_count, core, bus)

    @property
    def root(self) -> Envelope:
        return _buffer_of(self).job.root

    @property
    def finished(self) -> bool:
        buffer = _buffer_of(self)
        return buffer.control is not None or buffer.job.lifecycle == "finished"

    def request(self, *, stage: str, topic: str, payload: object, timeout_ms: int | None = None) -> EnvelopeId:
        return _mutate(self, lambda buffer: _request(buffer, stage, topic, payload, timeout_ms))

    def reply(self, body: object) -> None:
        _mutate(self, lambda buffer: _put_reply(buffer, body))

    def finish(self, body: object | None = None) -> None:
        _mutate(self, lambda buffer: _finish(buffer, body))

    def hold(self) -> Reply:
        return _mutate(self, _hold)


from eba.job.context_ops import _finish, _hold, _mutate, _request  # noqa: E402
