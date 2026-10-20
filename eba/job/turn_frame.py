from __future__ import annotations

from types import FrameType
from typing import Any

_DENIED = "runtime is the only writer"
_MISSING = object()


def _ints(value: object) -> tuple[int, ...]:
    if not isinstance(value, tuple):
        raise RuntimeError(_DENIED)
    found: list[int] = []
    for item in value:
        if not isinstance(item, int):
            raise RuntimeError(_DENIED)
        found.append(item)
    return tuple(found)


def _moved(sheet: Any, host_id: int, *, taken: bool) -> tuple[object, ...]:
    free = tuple(item for item in _ints(sheet[1]) if item != host_id)
    owned_ids = tuple(item for item in _ints(sheet[2]) if item != host_id)
    if taken:
        owned_ids = (*owned_ids, host_id)
    else:
        free = (*free, host_id)
    return ("eba-sheet", free, owned_ids)


def _calling_runtime(frame: FrameType | None) -> object:
    current = frame
    for _step in range(8):
        if current is None:
            return None
        found = current.f_locals.get("self")
        hosts = getattr(found, "_hosts", None)
        if isinstance(hosts, dict) and getattr(found, "_agenda", None) is not None:
            return found
        current = current.f_back
    return None
