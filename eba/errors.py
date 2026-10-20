from eba.envelope.envelope import Envelope

OUTBOX_FULL = "result outbox full"
REENTRANT = "reentrant host execution"


class BusError(Exception):
    pass


class MailboxFull(BusError):
    pass


class InvalidTopic(BusError):
    pass


class BackpressureError(Exception):
    pass


class DeliveryError(Exception):
    def __init__(self, envelope: Envelope, reason: str = "publication failed") -> None:
        super().__init__(reason)
        self.envelope = envelope


class OutboxFull(DeliveryError):
    def __init__(self, envelope: Envelope, reason: str = OUTBOX_FULL) -> None:
        super().__init__(envelope, reason)


class Reentrant(RuntimeError):
    def __init__(self) -> None:
        super().__init__(REENTRANT)


class LeasePending(RuntimeError):
    def __init__(self) -> None:
        super().__init__("lease release pending")


class WakeError(RuntimeError):
    pass


class ClockError(RuntimeError):
    pass


def combine_failures(original: Exception, secondary: Exception) -> Exception:
    grouped = ExceptionGroup("multiple failures", [original, secondary])
    chosen = secondary if isinstance(secondary, DeliveryError) else original
    if isinstance(chosen, DeliveryError):
        error = type(chosen)(chosen.envelope, str(chosen))
        error.__cause__ = grouped
        return error
    return grouped


_SETTLED = object()


def note_settled(error: Exception) -> Exception:
    if isinstance(error, (DeliveryError, WakeError, ClockError)):
        return error
    return mark_settled(error)


def mark_settled(error: Exception) -> Exception:
    setattr(error, "_eba_settled", _SETTLED)  # noqa: B010
    return error


def is_settled(error: BaseException) -> bool:
    return getattr(error, "_eba_settled", None) is _SETTLED
