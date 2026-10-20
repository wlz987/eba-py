from eba.envelope.envelope import Envelope, IdGen, make_envelope
from eba.envelope.header import Header, Request, copy_header
from eba.envelope.ids import ActorId
from eba.envelope.result import has_result_shape


class Matchmaker:
    def __init__(self, request: Header) -> None:
        header = copy_header(request)
        address = header.address
        if not isinstance(address, Request):
            raise TypeError("Matchmaker requires a request")
        self._topic = address.reply_to
        self._cause = header.cause
        self._correlation_id = header.id

    def reply(self, body: object, *, from_: ActorId | str, id_gen: IdGen) -> Envelope:
        if not has_result_shape(body):
            raise TypeError("invalid result body")
        return make_envelope(
            topic=self._topic,
            payload=body,
            from_=from_,
            id_gen=id_gen,
            cause=self._cause,
            kind="result",
            correlation_id=self._correlation_id,
        )
