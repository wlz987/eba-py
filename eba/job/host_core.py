from __future__ import annotations

import weakref
from typing import TYPE_CHECKING

from eba.job.core import Core

if TYPE_CHECKING:
    from eba.job.host import JobHost

_cores: weakref.WeakKeyDictionary[JobHost, Core] = weakref.WeakKeyDictionary()


def core_of(host: JobHost) -> Core:
    try:
        return _cores[host]
    except KeyError as error:
        raise RuntimeError("invalid JobHost") from error
