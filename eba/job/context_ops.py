from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, TypeVar

from eba.envelope.envelope import make_envelope
from eba.envelope.ids import EnvelopeId
from eba.envelope.result import has_result_shape
from eba.errors import BackpressureError
from eba.job.context import Context, Control, _Buffer, _Intent, _put_reply, _require_active
from eba.time.numbers import nonnegative_int

if TYPE_CHECKING:
    from eba.job.reply import Reply

T = TypeVar("T")


def _request(buffer: _Buffer, stage: str, topic: str, payload: object, timeout: int | None) -> EnvelopeId:
    if buffer.hold is not None:
        raise RuntimeError("job already held")
    if buffer.control is not None or buffer.job.lifecycle != "active":
        raise RuntimeError("job already finished")
    if buffer.pending_count + len(buffer.requests) >= buffer.job.max_inflight:
        raise BackpressureError("max_inflight")
    if timeout is not None:
        timeout = nonnegative_int(timeout, "timeout_ms")
    request = make_envelope(
        topic=topic,
        payload=payload,
        from_=buffer.actor_id,
        cause=buffer.job.root.header.cause,
        kind="request",
        reply_to=buffer.reply_to,
        id_gen=buffer.id_gen,
    )
    buffer.requests.append(_Intent(stage, request, timeout))
    return request.header.id


def _finish(buffer: _Buffer, body: object | None) -> None:
    if buffer.hold is not None:
        raise RuntimeError("job already held")
    if buffer.control is not None:
        return
    if body is not None:
        if buffer.job.root.header.kind == "request":
            _put_reply(buffer, body)
        elif not has_result_shape(body):
            raise TypeError("invalid result body")
    buffer.control = Control(body if isinstance(body, Mapping) else None)


def _mutate(ctx: Context, action: Callable[[_Buffer], T]) -> T:
    buffer = _require_active(ctx)
    if buffer.busy:
        raise RuntimeError("reentrant Context mutation")
    buffer.busy = True
    try:
        return action(buffer)
    finally:
        buffer.busy = False


def _hold(buffer: _Buffer) -> Reply:
    from eba.job.reply import Reply

    if buffer.hold is not None:
        raise RuntimeError("job already held")
    if buffer.control is not None or buffer.job.lifecycle != "active":
        raise RuntimeError("job already finished")
    if buffer.job.root.header.kind != "request":
        raise TypeError("root is not a request")
    if buffer.reply is not None or buffer.job.replied:
        raise RuntimeError("root already replied")
    if buffer.requests or buffer.pending_count:
        raise RuntimeError("cannot hold with pending requests")
    reply = Reply()
    buffer.core.held[buffer.job.root.header.id] = reply
    buffer.hold = reply
    buffer.job.held = True
    return reply
