from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from eba.mail.bus import Bus, Subscription


class _Live(Protocol):
    def active(self) -> bool: ...


def _noted(inbox_id: int, frame: list[tuple[int, object]]) -> list[object]:
    return [sub for iid, sub in frame if iid == inbox_id]


def _matched(granted: object, noted: list[object]) -> object | None:
    if isinstance(granted, Subscription):
        for sub in noted:
            if sub is granted:
                return granted
    if len(noted) == 1:
        return noted[0]
    return None


def _as_live(owner: object) -> _Live:
    active = getattr(owner, "active", None)
    if not callable(active):
        raise RuntimeError("lease does not carry its subscription")
    return cast(_Live, owner)


def _granted_owner(granted: object, noted: list[object]) -> _Live:
    return _as_live(_matched(granted, noted))


class _Closable(Protocol):
    def close(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class _Lease:
    target: _Closable
    owner: _Live


@dataclass(frozen=True, slots=True)
class _Route:
    lease: _Lease
    count: int
    bus: Bus

    @property
    def subscription(self) -> _Closable:
        return self.lease.target

    @property
    def owner(self) -> _Live:
        return self.lease.owner
