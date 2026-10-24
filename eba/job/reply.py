from __future__ import annotations

from collections.abc import Mapping

from eba.envelope.result import err_payload, err_payload_code, has_result_shape


class Reply:
    """A held request's one-shot slot. The runtime settles it on the next advance."""

    __slots__ = ("_body", "_closed")

    def __init__(self) -> None:
        self._body: Mapping[str, object] | None = None
        self._closed = False

    def send(self, body: object) -> None:
        if self._closed:
            raise RuntimeError("reply closed")
        if self._body is not None:
            raise RuntimeError("reply already settled")
        if not has_result_shape(body):
            raise TypeError("invalid result body")
        self._body = body

    def fail(self, error: str, code: int | None = None) -> None:
        self.send(err_payload(error) if code is None else err_payload_code(error, code))

    @property
    def is_closed(self) -> bool:
        return self._closed

    def _take(self) -> Mapping[str, object] | None:
        return self._body

    def _close(self) -> None:
        self._closed = True
