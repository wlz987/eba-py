from typing import NewType

EnvelopeId = NewType("EnvelopeId", str)
ActorId = NewType("ActorId", str)


def envelope_id(raw: str) -> EnvelopeId:
    if not isinstance(raw, str):
        raise TypeError("envelope id must be a string")
    return EnvelopeId(raw)


def actor_id(raw: str) -> ActorId:
    if not isinstance(raw, str):
        raise TypeError("actor id must be a string")
    return ActorId(raw)
