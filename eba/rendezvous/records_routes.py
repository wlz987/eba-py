from __future__ import annotations

from eba.rendezvous.lease import _Lease, _Route


class _RecordsRoutes:
    _routes: dict[int, dict[str, _Route]]
    _stuck: list[_Lease]

    def _ensure_routes(self, inbox_id: int) -> dict[str, _Route]:
        routes = self._routes.get(inbox_id)
        if routes is None:
            routes = {}
            self._routes[inbox_id] = routes
        return routes

    def _find_route(self, subscription: object) -> tuple[int, str] | None:
        for inbox_id, routes in self._routes.items():
            for topic, route in routes.items():
                if route.subscription is subscription:
                    return inbox_id, topic
        return None

    def _drop_route(self, inbox_id: int, topic: str) -> None:
        routes = self._routes.get(inbox_id)
        if routes is None:
            return
        routes.pop(topic, None)
        if not routes:
            self._routes.pop(inbox_id, None)

    def _recover_owed(self) -> None:
        kept: list[_Lease] = []
        for lease in self._stuck:
            found = self._find_route(lease.target)
            if not lease.owner.active():
                if found is not None:
                    inbox_id, topic = found
                    if self._routes[inbox_id][topic].count == 0:
                        self._drop_route(inbox_id, topic)
                continue
            if found is not None:
                inbox_id, topic = found
                if self._routes[inbox_id][topic].count > 0:
                    kept.append(lease)
                    continue
            try:
                lease.target.close()
            except Exception:
                kept.append(lease)
                continue
            if lease.owner.active():
                kept.append(lease)
                continue
            if found is not None:
                self._drop_route(inbox_id, topic)
        self._stuck = kept
