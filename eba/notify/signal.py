from __future__ import annotations

import weakref
from typing import NamedTuple, Protocol

READ = 1
TIMER = 2
WORK = 4
DELIVERY = 8
_MASK = 0xFFFFFFFF


class _Agenda(Protocol):
    signals: dict[str, weakref.ReferenceType[Signal]]

    def enqueue(self, actor: str) -> None: ...

    def unqueue(self, actor: str) -> None: ...


class _Binding(NamedTuple):
    actor: str
    owner: weakref.ReferenceType[_Agenda]


class Signal:
    __slots__ = ("__weakref__", "_binding", "_flags")

    def __init__(self) -> None:
        self._flags = 0
        self._binding: _Binding | None = None

    @property
    def is_bound(self) -> bool:
        found = self._binding
        return found is not None and found.owner() is not None

    def has(self, flag: int) -> bool:
        return (self._flags & flag) != 0

    def notify(self, flag: int) -> None:
        self._flags |= flag
        found = self._binding
        if found is None:
            return
        owner = found.owner()
        if owner is not None:
            owner.enqueue(found.actor)

    def clear(self, flag: int) -> None:
        self._flags &= ~flag & _MASK
        if self._flags:
            return
        found = self._binding
        if found is None:
            return
        owner = found.owner()
        if owner is not None:
            owner.unqueue(found.actor)

    def set(self, flag: int, ready: bool) -> None:
        if ready:
            self.notify(flag)
        else:
            self.clear(flag)

    def bound_to(self, owner: object) -> bool:
        found = self._binding
        return found is not None and found.owner() is owner

    def bind(self, owner: _Agenda, actor: str) -> None:
        self._binding = _Binding(actor, weakref.ref(owner))
        owner.signals[actor] = weakref.ref(self)
        if self._flags:
            owner.enqueue(actor)

    def detach(self) -> None:
        self._binding = None
