from __future__ import annotations

from collections.abc import Iterator

from eba.mail.inbox import Inbox, remember_route
from eba.mail.routes_detach import _RoutesDetach
from eba.mail.routes_types import Subscription as Subscription
from eba.mail.routes_types import _Entry, _key
from eba.notify.watch import Changes
from eba.pattern import Pattern, lookup_keys


class _Routes(_RoutesDetach):
    def __init__(self) -> None:
        self._indexes: dict[str, dict[str, dict[int, _Entry]]] = {
            "none": {},
            "star": {},
            "globstar": {},
        }
        self._by_inbox: dict[int, dict[tuple[str, str], _Entry]] = {}
        self.changes = Changes()

    def subscribe(self, pattern: Pattern, inbox: Inbox) -> None:
        key = _key(pattern)
        bucket = self._indexes[pattern.wildcard].setdefault(key[1], {})
        entry = bucket.get(inbox.id)
        added = entry is None
        if entry is None:
            entry = _Entry(inbox, pattern, 0)
            bucket[inbox.id] = entry
            group = self._by_inbox.get(inbox.id)
            if group is None:
                group = {}
                self._by_inbox[inbox.id] = group
                remember_route(inbox, self)
            group[key] = entry
        entry.count += 1
        if not added:
            return
        try:
            self.changes.notify(pattern)
        except Exception:
            self._detach(pattern, inbox)
            raise

    def bind(self, pattern: Pattern, inbox: Inbox, right: Subscription) -> None:
        key = _key(pattern)
        bucket = self._indexes[pattern.wildcard].get(key[1])
        entry = None if bucket is None else bucket.get(inbox.id)
        if entry is not None:
            entry.rights.append(right)

    def _buckets(self, parts: list[str]) -> Iterator[dict[int, _Entry]]:
        for wildcard, key in lookup_keys(parts):
            bucket = self._indexes[wildcard].get(key)
            if bucket:
                yield bucket

    def snapshot_match(self, parts: list[str]) -> list[Inbox]:
        targets: dict[int, Inbox] = {}
        for bucket in self._buckets(parts):
            for inbox_id, entry in bucket.items():
                targets.setdefault(inbox_id, entry.inbox)
        return list(targets.values())

    def hold_count(self, parts: list[str], inbox: Inbox) -> int:
        total = 0
        for bucket in self._buckets(parts):
            entry = bucket.get(inbox.id)
            if entry is not None and entry.inbox is inbox:
                total += entry.count
        return total
