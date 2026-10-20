from __future__ import annotations

from dataclasses import dataclass

from eba.envelope.ids import EnvelopeId
from eba.envelope.result import Completion
from eba.mail.inbox import Inbox


class _Record:
    __slots__ = ("cause", "continuation", "inbox", "topic")

    def __init__(self, topic: str, cause: EnvelopeId, continuation: object, inbox: Inbox) -> None:
        self.topic = topic
        self.cause = cause
        self.continuation = continuation
        self.inbox = inbox


@dataclass(frozen=True, slots=True)
class Claim:
    continuation: object
    completion: Completion
