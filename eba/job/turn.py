from __future__ import annotations

import sys
import weakref
from typing import Any

from eba.job.turn_frame import _DENIED, _MISSING, _calling_runtime, _ints, _moved
from eba.job.turn_roster import _agree


def require(
    host: object,
    _clock: object = _MISSING,
    *,
    owned: bool = False,
    op: str | None = None,
    _sheet: object = _MISSING,
) -> None:
    writers: Any = ("eba-writers",)
    sheet: Any = ("eba-sheet",)
    caller = sys._getframe(1).f_code
    try:
        above = sys._getframe(2)
    except ValueError:
        above = None
    grand = above.f_code if above is not None else None
    if not isinstance(writers, frozenset) or not isinstance(sheet, tuple) or len(sheet) != 3:
        raise RuntimeError(_DENIED)
    if op == "born":
        from eba.job.host import JobHost

        if caller is not JobHost.__init__.__code__:
            raise RuntimeError(_DENIED)
        _retarget(_moved(sheet, id(host), taken=False))
        return
    if op is not None:
        if caller not in writers:
            raise RuntimeError(_DENIED)
        host_id = id(host)
        if op == "admit":
            if host_id in _ints(sheet[2]) or host_id not in _ints(sheet[1]):
                raise RuntimeError(_DENIED)
            return
        if op == "claim":
            runtime = _calling_runtime(sys._getframe(1))
            if runtime is None:
                raise RuntimeError(_DENIED)
            try:
                setattr(host, "_writer", weakref.ref(runtime))  # noqa: B010
            except AttributeError:
                raise RuntimeError(_DENIED) from None
            _retarget(_moved(sheet, host_id, taken=True))
            return
        if op == "release":
            setattr(host, "_writer", None)  # noqa: B010
            _retarget(_moved(sheet, host_id, taken=False))
            return
        raise RuntimeError(_DENIED)
    if grand in writers:
        ref = getattr(host, "_writer", None)
        if ref is None:
            if owned or grand is None or grand.co_name != "add":
                raise RuntimeError(_DENIED)
            return
        owner = ref() if isinstance(ref, weakref.ref) else None
        if owner is None or _calling_runtime(above) is not owner:
            raise RuntimeError(_DENIED)
        return
    if _sheet is not sheet:
        raise RuntimeError(_DENIED)
    _agree(sheet)
    host_id = id(host)
    if owned or host_id not in _ints(sheet[1]) or host_id in _ints(sheet[2]):
        raise RuntimeError(_DENIED)


from eba.job.turn_install import _retarget as _retarget  # noqa: E402
from eba.job.turn_install import install_roster as install_roster  # noqa: E402
from eba.job.turn_install import install_writers as install_writers  # noqa: E402
