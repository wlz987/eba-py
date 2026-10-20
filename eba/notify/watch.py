from __future__ import annotations

import weakref
from collections.abc import Callable

from eba.notify.signal import DELIVERY, Signal
from eba.pattern import Pattern, lookup_keys


class Interest:
    def __init__(self, signal: Signal, candidates: dict[str, None], topic: str) -> None:
        self.key = object()
        self.owners: set[Watchers] = set()
        self.signal = signal
        self.candidates = candidates
        self.topic = topic

    def notify(self) -> None:
        self.candidates[self.topic] = None
        self.signal.notify(DELIVERY)

    def dispose(self) -> None:
        for owner in list(self.owners):
            owner.remove(self)
        self.owners.clear()


class Watchers:
    def __init__(self, on_empty: Callable[[], None] | None = None) -> None:
        self._waiting: dict[object, weakref.ReferenceType[Interest]] = {}
        self._on_empty = on_empty

    def watch(self, interest: Interest) -> None:
        self._waiting[interest.key] = weakref.ref(interest)
        interest.owners.add(self)

    def remove(self, interest: Interest) -> None:
        self._waiting.pop(interest.key, None)
        if not self._waiting and self._on_empty is not None:
            self._on_empty()

    def notify(self) -> None:
        waiting = list(self._waiting.values())
        self._waiting.clear()
        if self._on_empty is not None:
            self._on_empty()
        error: Exception | None = None
        for weak in waiting:
            interest = weak()
            if interest is None:
                continue
            interest.owners.discard(self)
            try:
                interest.notify()
            except Exception as caught:
                if error is None:
                    error = caught
        if error is not None:
            raise error


class Changes:
    def __init__(self) -> None:
        self._indexes: dict[str, dict[str, Watchers]] = {
            "none": {},
            "star": {},
            "globstar": {},
        }

    def watch(self, topic: str, interest: Interest) -> None:
        for kind, key in lookup_keys(topic.split(".")):
            self._watch_key(kind, key, interest)

    def notify(self, pattern: Pattern) -> None:
        watchers = self._indexes[pattern.wildcard].get(".".join(pattern.literal))
        if watchers is not None:
            watchers.notify()

    def _watch_key(self, kind: str, key: str, interest: Interest) -> None:
        index = self._indexes[kind]
        source = index.get(key)
        if source is None:
            holder: dict[str, Watchers] = {}

            def on_empty() -> None:
                if index.get(key) is holder.get("source"):
                    index.pop(key, None)

            source = Watchers(on_empty)
            holder["source"] = source
            index[key] = source
        source.watch(interest)
