from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from eba.mail.inbox import Inbox
from eba.pattern import Pattern


class Subscription:
    __slots__ = ("_release",)

    def __init__(self, release: Callable[[], bool]) -> None:
        self._release: Callable[[], bool] | None = release

    def active(self) -> bool:
        return self._release is not None

    def _disarm(self) -> None:
        self._release = None

    def disarm(self) -> None:
        self._disarm()

    def close(self) -> bool:
        release = self._release
        if release is None:
            return False
        return release()


@dataclass
class _Entry:
    inbox: Inbox
    pattern: Pattern
    count: int
    rights: list[Subscription] = field(default_factory=list)


def _key(pattern: Pattern) -> tuple[str, str]:
    return pattern.wildcard, ".".join(pattern.literal)
