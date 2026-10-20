from __future__ import annotations

from eba.mail.inbox import Inbox, forget_route
from eba.mail.routes_types import Subscription, _Entry, _key
from eba.notify.watch import Changes
from eba.pattern import Pattern


class _RoutesDetach:
    _by_inbox: dict[int, dict[tuple[str, str], _Entry]]
    _indexes: dict[str, dict[str, dict[int, _Entry]]]
    changes: Changes

    def _detach(
        self,
        pattern: Pattern,
        inbox: Inbox,
        right: Subscription | None = None,
    ) -> tuple[bool, Pattern | None]:
        key = _key(pattern)
        bucket = self._indexes[pattern.wildcard].get(key[1])
        if bucket is None or inbox.id not in bucket:
            if right is not None:
                right._disarm()
            return False, None
        entry = bucket[inbox.id]
        if right is not None:
            entry.rights = [item for item in entry.rights if item is not right]
        if entry.count > 1:
            entry.count -= 1
            if right is not None:
                right._disarm()
            return True, None
        del bucket[inbox.id]
        if not bucket:
            del self._indexes[pattern.wildcard][key[1]]
        group = self._by_inbox.get(inbox.id)
        if group is not None:
            group.pop(key, None)
            if not group:
                del self._by_inbox[inbox.id]
                forget_route(inbox, self)
        if right is not None:
            right._disarm()
        return True, entry.pattern

    def unsubscribe_all(self, inbox: Inbox) -> None:
        group = self._by_inbox.pop(inbox.id, None)
        if group is None:
            return
        patterns = []
        for (wildcard, text), entry in group.items():
            bucket = self._indexes[wildcard].get(text)
            if bucket is not None:
                bucket.pop(inbox.id, None)
                if not bucket:
                    del self._indexes[wildcard][text]
            for item in entry.rights:
                item._disarm()
            patterns.append(entry.pattern)
        for pattern in patterns:
            self.changes.notify(pattern)
