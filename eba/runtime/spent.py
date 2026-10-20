from __future__ import annotations

import sys

from eba.envelope.envelope import Envelope, IdGen, make_envelope
from eba.envelope.result import err_payload
from eba.errors import DeliveryError
from eba.job.host import JobHost
from eba.mail.bus import Bus
from eba.notify.agenda import Agenda
from eba.time.clock import Clock

_DENIED = "runtime is the only writer"


class _RuntimeSpent:
    _hosts: dict[str, JobHost]
    _bus: Bus
    _id_gen: IdGen
    _agenda: Agenda

    def advance(self) -> bool:
        raise NotImplementedError

    def _answer_spent(self, error: DeliveryError, clock: Clock) -> None:
        if sys._getframe(1).f_code is not self.advance.__code__:
            raise RuntimeError(_DENIED)
        envelope = error.envelope
        request_id = envelope.header.correlation_id
        if envelope.header.kind != "result" or request_id is None or not self._spent(envelope):
            return
        failure = make_envelope(
            topic=envelope.header.topic,
            payload=err_payload("delivery_failed"),
            from_=envelope.header.from_,
            id_gen=self._id_gen,
            cause=envelope.header.cause,
            kind="result",
            correlation_id=request_id,
        )
        held = False
        for host in self._hosts.values():

            def project(bound: JobHost = host) -> None:
                JobHost.project(bound, self._agenda)

            if JobHost.resume_held(host, request_id, failure, self._bus, clock, self._id_gen, project):
                held = True
        if not held:
            self._bus.deliver(failure, self._agenda)

    def _spent(self, envelope: Envelope) -> bool:
        if sys._getframe(1).f_code is not self._answer_spent.__code__:
            raise RuntimeError(_DENIED)
        for host in self._hosts.values():  # noqa: SIM110
            if JobHost.delivery_spent(host, envelope):
                return True
        return False
