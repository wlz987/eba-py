from __future__ import annotations

import weakref
from typing import TYPE_CHECKING

from eba.envelope.result import has_result_shape
from eba.job.context_state import Commit
from eba.job.context_types import _Buffer

if TYPE_CHECKING:
    from eba.job.context import Context

_buffers: weakref.WeakKeyDictionary[Context, _Buffer] = weakref.WeakKeyDictionary()

if TYPE_CHECKING:
    from eba.job.context import Context


def seal_context(ctx: Context) -> Commit:
    buffer = _buffer_of(ctx)
    buffer.id_gen = None
    return Commit(buffer.requests, buffer.reply, buffer.control)


def _buffer_of(ctx: Context) -> _Buffer:
    try:
        return _buffers[ctx]
    except KeyError as error:
        raise RuntimeError("invalid Context") from error


def _require_active(ctx: Context) -> _Buffer:
    buffer = _buffer_of(ctx)
    if buffer.id_gen is None:
        raise RuntimeError("Context is valid only during its callback")
    return buffer


def _put_reply(buffer: _Buffer, body: object) -> None:
    if buffer.job.root.header.kind != "request":
        raise TypeError("root is not a request")
    if buffer.reply is not None or buffer.job.replied:
        raise RuntimeError("root already replied")
    if not has_result_shape(body):
        raise TypeError("invalid result body")
    buffer.reply = body
