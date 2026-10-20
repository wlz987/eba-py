from dataclasses import dataclass
from typing import Protocol

from eba.envelope.header import (
    Header,
    validate_header,
)
from eba.envelope.ids import EnvelopeId


class IdGen(Protocol):
    def next_envelope_id(self) -> EnvelopeId: ...


@dataclass(frozen=True, slots=True)
class Envelope:
    header: Header
    payload: object

    def __post_init__(self) -> None:
        if not isinstance(self.header, Header):
            raise TypeError("expected Header")
        validate_header(self.header)


from eba.envelope.build import checked_envelope as checked_envelope  # noqa: E402
from eba.envelope.build import make_envelope as make_envelope  # noqa: E402
