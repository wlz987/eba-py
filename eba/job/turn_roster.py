from __future__ import annotations

from types import CodeType
from typing import Any

_DENIED = "runtime is the only writer"


def _sheet_in(code: CodeType) -> object:
    found: object = None
    for item in code.co_consts:
        if isinstance(item, tuple) and len(item) == 3 and item[0] == "eba-sheet":
            if found is not None:
                raise RuntimeError(_DENIED)
            found = item
    if found is None:
        raise RuntimeError(_DENIED)
    return found


def _doors() -> tuple[Any, ...]:
    from eba.job.host import JobHost

    return (
        JobHost.__init__,
        JobHost.attach,
        JobHost.withdraw,
        JobHost.bind,
        JobHost.unbind,
        JobHost.advance,
        JobHost.notice_closed_inbox,
        JobHost.drain,
        JobHost.begin_close,
        JobHost.close_owned,
        JobHost.take_abandoned,
        JobHost.project,
        JobHost.delivery_spent,
        JobHost.resume_held,
    )


def _agree(found: object) -> None:
    for fn in _doors():
        if _sheet_in(fn.__code__) is not found:
            raise RuntimeError(_DENIED)


def _lay(fn: Any, sheet: object) -> None:
    code = fn.__code__
    found = False
    consts: list[object] = []
    for item in code.co_consts:
        if isinstance(item, tuple) and item and item[0] == "eba-sheet":
            consts.append(sheet)
            found = True
        else:
            consts.append(item)
    if not found:
        raise RuntimeError(_DENIED)
    fn.__code__ = code.replace(co_consts=tuple(consts))


def _swap(fn: Any, marker: object, value: object) -> None:
    code = fn.__code__
    found = False
    consts: list[object] = []
    for item in code.co_consts:
        if item == marker:
            consts.append(value)
            found = True
        else:
            consts.append(item)
    if not found:
        raise RuntimeError(_DENIED)
    fn.__code__ = code.replace(co_consts=tuple(consts))
