from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Literal

from eba.envelope.envelope import Envelope
from eba.envelope.ids import ActorId, EnvelopeId
from eba.job.book import RequestBook
from eba.job.job import Job, state_of
from eba.job.outbox import Outbox
from eba.job.reply import Reply
from eba.mail.inbox import Receiver, read_signal, remove
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
        self.cancel_errors = 0
        self.last_cancel_error: str | None = None
        self.cancel_pending: set[EnvelopeId] = set()
        self.abandoned: list[Envelope] | None = None
        self.pending: Envelope | None = None
        self.pending_job: Job | None = None
        self.rest: deque[tuple[Envelope, Job | None]] = deque()
        self.again: set[int] = set()
        self.attempts: dict[int, int] = {}
        self.kept: dict[int, Envelope] = {}

    def take_cancelled(self) -> list[EnvelopeId]:
        return self.book.take_cancelled()

    def cancel_queued(self, request_ids: list[EnvelopeId]) -> None:
        if not request_ids:
            return
        wanted = set(request_ids)
        self.queue.remove(lambda item: isinstance(item, Envelope) and item.header.id in wanted)
        for request_id in request_ids:
            remove(self.sub.inbox, request_id)

    def cancel_jobs(self, request_ids: list[EnvelopeId]) -> None:
        from eba.job.cancel_job import cancel_job

        for request_id in request_ids:
            job = self.jobs.get(request_id)
            if job is None:
                self.cancel_pending.discard(request_id)
                continue
            state = state_of(job)
            if state.lifecycle != "active" or state.held:
                self.cancel_pending.discard(request_id)
                continue
            if not cancel_job(self, job):
                self.cancel_pending.add(request_id)

    def take_pending_cancels(self) -> set[EnvelopeId]:
        found = self.cancel_pending
        self.cancel_pending = set()
        return found

    def cancel_held(self, request_ids: list[EnvelopeId]) -> None:
        for request_id in request_ids:
            reply = self.held.get(request_id)
            if reply is None or reply.is_closed or reply._take() is not None:
                continue
            reply.fail("cancelled")

    def begin_close(self) -> list[Envelope]:
        if self.abandoned is None:
            self.abandoned = []
        if self.state != "closed":
            self.state = "closing"
        return self.abandoned
