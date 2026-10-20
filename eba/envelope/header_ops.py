from __future__ import annotations

from eba.envelope.errors import EnvelopeBuildError
from eba.envelope.header import Address, Diagnostic, Event, Header, Request, ResultAddress
from eba.envelope.topic import split_topic


def validate_header(header: Header) -> None:
    if not isinstance(header.id, str) or not header.id:
        raise EnvelopeBuildError("id must be a nonempty string")
    if not isinstance(header.cause, str) or not header.cause:
        raise EnvelopeBuildError("cause must be a nonempty string")
    if not isinstance(header.from_, str):
        raise EnvelopeBuildError("from must be a string")
    split_topic(header.topic)
    address = header.address
    if isinstance(address, Request):
        split_topic(address.reply_to)
    elif isinstance(address, ResultAddress):
        if not isinstance(address.correlation_id, str) or not address.correlation_id:
            raise EnvelopeBuildError("correlation_id must be nonempty")
    elif not isinstance(address, (Event, Diagnostic)):
        raise EnvelopeBuildError("invalid message kind or protocol address")


def copy_header(header: Header) -> Header:
    if not isinstance(header, Header):
        raise TypeError("expected Header")
    address = header.address
    if isinstance(address, Request):
        copied: Address = Request(address.reply_to)
    elif isinstance(address, ResultAddress):
        copied = ResultAddress(address.correlation_id)
    elif isinstance(address, Diagnostic):
        copied = Diagnostic()
    elif isinstance(address, Event):
        copied = Event()
    else:
        raise EnvelopeBuildError("invalid message kind or protocol address")
    return Header(
        id=header.id,
        topic=header.topic,
        from_=header.from_,
        cause=header.cause,
        address=copied,
    )
