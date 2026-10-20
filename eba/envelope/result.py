from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeGuard, cast

from eba.envelope.envelope import Envelope
from eba.envelope.ids import EnvelopeId

_RESERVED = frozenset({"ok", "error", "value"})


@dataclass(frozen=True, slots=True)
class Completion:
    request_id: EnvelopeId
    body: Mapping[str, object] | None

    @property
    def is_timeout(self) -> bool:
        return self.body is None


def ok_payload(value: object) -> dict[str, object]:
    return {"ok": True, "value": value}


def err_payload(error: str, detail: Mapping[str, object] | None = None) -> dict[str, object]:
    if not isinstance(error, str):
        raise TypeError("error must be a string")
    extra = {} if detail is None else dict(detail)
    for key in extra:
        if key in _RESERVED:
            raise ValueError(f"reserved result key: {key!r}")
    return {"ok": False, "error": error, **extra}


def is_result_ok(body: object) -> bool:
    record = _record(body)
    return record is not None and record.get("ok") is True and "value" in record


def is_result_err(body: object) -> bool:
    record = _record(body)
    return record is not None and record.get("ok") is False and isinstance(record.get("error"), str)


def has_result_shape(body: object) -> TypeGuard[Mapping[str, object]]:
    return is_result_ok(body) or is_result_err(body)


def result_value(body: Mapping[str, object]) -> object:
    if not is_result_ok(body):
        raise TypeError("result body is not Ok")
    return body["value"]


def result_error(body: Mapping[str, object]) -> str:
    if not is_result_err(body):
        raise TypeError("result body is not Err")
    return cast(str, body["error"])


def result_body(envelope: Envelope) -> Mapping[str, object] | None:
    payload = envelope.payload
    if envelope.header.kind == "result" and has_result_shape(payload):
        return payload
    return None


def result_request_id(envelope: Envelope) -> EnvelopeId | None:
    if envelope.header.kind != "result":
        return None
    return envelope.header.correlation_id


def _record(body: object) -> Mapping[str, object] | None:
    if not isinstance(body, Mapping) or isinstance(body, (str, bytes)):
        return None
    return body
