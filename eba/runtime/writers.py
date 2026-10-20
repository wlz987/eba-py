from __future__ import annotations

from types import CodeType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eba.runtime.runtime import Runtime


def install_writers(runtime: type[Runtime]) -> None:
    from eba.job.turn import install_writers

    codes: list[CodeType] = [
        runtime.add.__code__,
        runtime.advance.__code__,
        runtime.close.__code__,
        runtime._answer_spent.__code__,
        runtime._spent.__code__,
        runtime._drain.__code__,
    ]
    for const in runtime._answer_spent.__code__.co_consts:
        if isinstance(const, CodeType) and const.co_name == "project":
            codes.append(const)  # noqa: PERF401
    install_writers(frozenset(codes))
    import eba.job.turn as turn
    import eba.job.turn_roster as roster

    del turn.install_writers
    del roster._swap
