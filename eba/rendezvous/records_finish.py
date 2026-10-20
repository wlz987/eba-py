from __future__ import annotations

from typing import cast

from eba.envelope.ids import EnvelopeId
from eba.rendezvous.lease import _Closable, _granted_owner, _Lease, _noted, _Route
from eba.rendezvous.record import _Record
from eba.time.deadlines import Deadlines


class _RecordsFinish:
    _deadlines: Deadlines[EnvelopeId]
    _entries: dict[EnvelopeId, _Record]
    _routes: dict[int, dict[str, _Route]]
    _stuck: list[_Lease]

    def _owe(self, lease: _Lease) -> None:
        if all(item.target is not lease.target for item in self._stuck):
            self._stuck.append(lease)

    def _paid(self, lease: _Lease) -> None:
        self._stuck = [item for item in self._stuck if item.target is not lease.target]

    def _roll_back(self, granted: _Closable | None, frame: list[tuple[int, object]], inbox_id: int) -> None:
        noted = _noted(inbox_id, frame)
        targets: list[object] = []
        if granted is not None:
            targets.append(granted)
        for sub in noted:
            if all(sub is not item for item in targets):
                targets.append(sub)
        for target in targets:
            close = getattr(target, "close", None)
            if not callable(close):
                continue
            try:
                close()
            except Exception:
                try:
                    live = _granted_owner(target, noted)
                except RuntimeError:
                    continue
                if not live.active():
                    continue
                self._owe(_Lease(cast(_Closable, target), live))
