from dataclasses import dataclass
from typing import Literal

from eba.envelope.ids import ActorId, EnvelopeId

Kind = Literal["event", "request", "result", "diagnostic"]


@dataclass(frozen=True, slots=True)
class Event:
    pass


@dataclass(frozen=True, slots=True)
class Diagnostic:
    pass


@dataclass(frozen=True, slots=True)
class Request:
    reply_to: str


@dataclass(frozen=True, slots=True)
class ResultAddress:
    correlation_id: EnvelopeId


Address = Event | Diagnostic | Request | ResultAddress


@dataclass(frozen=True, slots=True)
class Header:
    id: EnvelopeId
    topic: str
    from_: ActorId
    cause: EnvelopeId
    address: Address

    def __post_init__(self) -> None:
        validate_header(self)

    @property
    def kind(self) -> Kind:
        address = self.address
        if isinstance(address, Event):
            return "event"
        if isinstance(address, Request):
            return "request"
        if isinstance(address, ResultAddress):
            return "result"
        return "diagnostic"

    @property
    def reply_to(self) -> str | None:
        address = self.address
        if isinstance(address, Request):
            return address.reply_to
        return None

    @property
    def correlation_id(self) -> EnvelopeId | None:
        address = self.address
        if isinstance(address, ResultAddress):
            return address.correlation_id
        return None


from eba.envelope.header_ops import copy_header as copy_header  # noqa: E402
from eba.envelope.header_ops import validate_header as validate_header  # noqa: E402
