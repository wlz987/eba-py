from eba.envelope.envelope import Envelope, IdGen, make_envelope
from eba.envelope.ids import ActorId, actor_id
from eba.errors import DeliveryError
from eba.mail.bus import Bus


class Publisher:
    def __init__(self, actor: ActorId | str) -> None:
        self.actor_id = actor_id(actor)

    def emit(
        self,
        bus: Bus,
        *,
        topic: str,
        payload: object,
        id_gen: IdGen,
    ) -> Envelope:
        envelope = make_envelope(
            topic=topic,
            payload=payload,
            from_=self.actor_id,
            id_gen=id_gen,
        )
        try:
            bus.publish(envelope)
        except Exception as error:
            raise DeliveryError(envelope) from error
        return envelope
