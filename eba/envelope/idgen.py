import uuid

from eba.envelope.ids import EnvelopeId, envelope_id


class SeqIdGen:
    def __init__(self, start: int = 1) -> None:
        if isinstance(start, bool) or not isinstance(start, int):
            raise TypeError("start must be an int")
        if start < 0:
            raise ValueError("start must be nonnegative")
        self._n = start

    def next_envelope_id(self) -> EnvelopeId:
        current = self._n
        self._n = current + 1
        return envelope_id(f"{current:032x}")


class UuidIdGen:
    def next_envelope_id(self) -> EnvelopeId:
        return envelope_id(uuid.uuid4().hex)
