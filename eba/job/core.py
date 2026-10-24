from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Literal

from eba.envelope.envelope import Envelope
from eba.envelope.ids import ActorId, EnvelopeId
from eba.job.book import RequestBook
from eba.job.job import Job
from eba.job.outbox import Outbox
from eba.job.reply import Reply
from eba.mail.inbox import Receiver, read_signal
from eba.mail.queue import Queue
from eba.mail.subscriber import Subscriber
from eba.time.numbers import nonnegative_int, positive_int

HostState = Literal["running", "draining", "closing", "closed"]


class Core:
    def __init__(
        self,
        *,
        actor_id: ActorId | str,
        receiver: Receiver,
        patterns: list[str] | tuple[str, ...],
        request_timeout_ms: int | None,
        queue_limit: int,
        active_limit: int,
        work_budget: int,
        outbox_limit: int,
        make_job: Callable[[Envelope], Job],
        on_rejected: Callable[[Envelope, str], None],
    ) -> None:
        self.make_job = make_job
        self.on_rejected = on_rejected
        pattern_text = tuple(patterns)
        self.active_limit = positive_int(active_limit, "active_limit")
        self.work_budget = positive_int(work_budget, "work_budget")
        self.timeout = None if request_timeout_ms is None else nonnegative_int(request_timeout_ms, "request_timeout_ms")
        outbox_checked = positive_int(outbox_limit, "outbox_limit")
        self.queue = Queue(queue_limit)
        self.sub = Subscriber(actor_id, receiver, pattern_text)
        self.signal = read_signal(self.sub.inbox)
        self.outbox = Outbox(outbox_checked, self.signal)
        self.jobs: dict[EnvelopeId, Job] = {}
        self.held: dict[EnvelopeId, Reply] = {}
        self.book = RequestBook()
        self.phase = 0
        self.busy = False
        self.state: HostState = "running"
        self.rejected_count = 0
        self.abandoned: list[Envelope] | None = None
        self.pending: Envelope | None = None
        self.pending_job: Job | None = None
        self.rest: deque[tuple[Envelope, Job | None]] = deque()
        self.again: set[int] = set()
        self.attempts: dict[int, int] = {}
        self.kept: dict[int, Envelope] = {}

    def begin_close(self) -> list[Envelope]:
        if self.abandoned is None:
            self.abandoned = []
        if self.state != "closed":
            self.state = "closing"
        return self.abandoned
