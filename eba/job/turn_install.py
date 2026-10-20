from __future__ import annotations

import sys
from types import CodeType

from eba.job.turn import require
from eba.job.turn_frame import _DENIED
from eba.job.turn_roster import _doors, _lay, _swap


def _retarget(sheet: tuple[object, ...]) -> None:
    if sys._getframe(1).f_code is not require.__code__:
        raise RuntimeError(_DENIED)
    _lay(require, sheet)
    for fn in _doors():
        _lay(fn, sheet)


def install_roster() -> None:
    sheet = ("eba-sheet", (), ())
    _lay(require, sheet)
    for fn in _doors():
        _lay(fn, sheet)


def install_writers(codes: frozenset[CodeType]) -> None:
    _swap(require, ("eba-writers",), codes)
