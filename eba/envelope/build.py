from __future__ import annotations

from eba.envelope.envelope import Envelope, IdGen
from eba.envelope.errors import EnvelopeBuildError
from eba.envelope.header import (
    Address,
    Diagnostic,
    Event,
    Header,
    Request,
    ResultAddress,
    copy_header,
    validate_header,
)
from eba.envelope.ids import ActorId, EnvelopeId, actor_id, envelope_id


def make_envelope(
    *,
    topic: str,
    payload: object,
    from_: ActorId | str,
    cause: EnvelopeId | str | None = None,
    id: EnvelopeId | str | None = None,
    id_gen: IdGen | None = None,
    kind: str = "event",
    reply_to: str | None = None,
    correlation_id: EnvelopeId | str | None = None,
) -> Envelope:
    assigned = _assign_id(id, id_gen)
    address = _address(kind, reply_to, correlation_id)
    header = Header(
        id=assigned,
        topic=topic,
        from_=_actor(from_),
        cause=assigned if cause is None else _cause(cause),
        address=address,
    )
    return Envelope(header, payload)


def checked_envelope(envelope: Envelope) -> Envelope:
    if type(envelope) is Envelope:
        if not isinstance(envelope.header, Header):
            raise TypeError("expected Header")
        validate_header(envelope.header)
        return envelope
    if not isinstance(envelope, Envelope):
        raise TypeError("expected Envelope")
    return Envelope(copy_header(envelope.header), envelope.payload)


def _assign_id(id: EnvelopeId | str | None, id_gen: IdGen | None) -> EnvelopeId:
    assigned: EnvelopeId | str | None
    if id is None:
        if id_gen is None:
            raise EnvelopeBuildError("id_gen is required when id is omitted")
        assigned = id_gen.next_envelope_id()
    else:
        assigned = id if isinstance(id, str) else None
    if not isinstance(assigned, str) or not assigned:
        raise EnvelopeBuildError("id must be a nonempty string")
    return envelope_id(assigned)


def _cause(cause: EnvelopeId | str) -> EnvelopeId:
    if not isinstance(cause, str) or not cause:
        raise EnvelopeBuildError("cause must be a nonempty string")
    return envelope_id(cause)


def _actor(sender: ActorId | str) -> ActorId:
    if not isinstance(sender, str):
        raise EnvelopeBuildError("from must be a string")
    return actor_id(sender)


def _address(
    kind: str,
    reply_to: str | None,
    correlation_id: EnvelopeId | str | None,
) -> Address:
    if kind == "request":
        if correlation_id is not None:
            raise EnvelopeBuildError("request cannot have correlation_id")
        if not isinstance(reply_to, str):
            raise EnvelopeBuildError("request requires reply_to")
        return Request(reply_to)
    if kind == "result":
        if reply_to is not None or not isinstance(correlation_id, str) or not correlation_id:
            raise EnvelopeBuildError("result requires only correlation_id")
        return ResultAddress(envelope_id(correlation_id))
    if kind in {"event", "diagnostic"}:
        if reply_to is not None or correlation_id is not None:
            raise EnvelopeBuildError("invalid message kind or protocol address")
        if kind == "event":
            return Event()
        return Diagnostic()
    raise EnvelopeBuildError("invalid message kind or protocol address")
