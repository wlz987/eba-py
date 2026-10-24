from eba import Bus, Inbox, Job, JobHost, ManualClock, Runtime, SeqIdGen
from eba.errors import LeasePending
from eba.job import Caller
from eba.job.call import settled
from eba.job.host_core import core_of

finished = []
begun = []
active_finished = []


class Hold(Job):
    def begin(self, ctx) -> None:
        begun.append(1)
        ctx.hold()

    def on_finished(self, body) -> None:
        finished.append(body)


class HoldHost(JobHost):
    def make_job(self, root):
        return Hold(root)


class Active(Job):
    def begin(self, ctx) -> None:
        ctx.request(stage="inner", topic="orphan.work", payload={"n": 3})

    def on_finished(self, body) -> None:
        active_finished.append(body)


class ActiveHost(JobHost):
    def make_job(self, root):
        return Active(root)


class Bad(Job):
    def begin(self, ctx) -> None:
        ctx.request(stage="inner", topic="orphan.work", payload={"n": 4})

    def on_finished(self, body) -> None:
        raise RuntimeError("cleanup boom")


class BadHost(JobHost):
    def make_job(self, root):
        return Bad(root)


def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    runtime.add(HoldHost(actor_id="hold", receiver=Inbox(8).receiver(), patterns=["orphan.work"]))
    runtime.add(ActiveHost(actor_id="active", receiver=Inbox(8).receiver(), patterns=["active"]))
    bad_host = BadHost(actor_id="bad", receiver=Inbox(8).receiver(), patterns=["bad"])
    runtime.add(bad_host)
    caller = Caller(Inbox(8).receiver(), runtime.id_gen)
    runtime.add(caller)
    root = caller.admit(topic="orphan.work", payload={"n": 1}, from_="orphan")
    for _ in range(12):
        runtime.advance()
    cancelled = caller.cancel(root.header.id)
    for _ in range(12):
        runtime.advance()

    completion = settled(root)
    body = completion.body if completion is not None else None
    if not cancelled or not isinstance(body, dict) or body.get("error") != "cancelled":
        raise SystemExit(f"orphan caller: {cancelled} {body!r}")
    if len(finished) != 1 or not isinstance(finished[0], dict) or finished[0].get("error") != "cancelled":
        raise SystemExit(f"orphan holder: {finished!r}")

    queued_root = caller.admit(topic="orphan.work", payload={"n": 2}, from_="orphan")
    runtime.advance()
    assert caller.cancel(queued_root.header.id)
    for _ in range(4):
        runtime.advance()
    queued_completion = settled(queued_root)
    queued_body = queued_completion.body if queued_completion is not None else None
    if (
        len(begun) != 1
        or len(finished) != 1
        or not isinstance(queued_body, dict)
        or queued_body.get("error") != "cancelled"
    ):
        raise SystemExit(f"orphan queued: begun={begun!r} finished={finished!r} body={queued_body!r}")

    active_root = caller.admit(topic="active", payload={}, from_="orphan")
    for _ in range(8):
        runtime.advance()
    active_cancelled = caller.cancel(active_root.header.id)
    for _ in range(8):
        runtime.advance()
    active_completion = settled(active_root)
    active_body = active_completion.body if active_completion is not None else None
    if (
        not active_cancelled
        or len(begun) != 2
        or len(finished) != 2
        or len(active_finished) != 1
        or not isinstance(active_body, dict)
        or active_body.get("error") != "cancelled"
        or not isinstance(active_finished[0], dict)
        or active_finished[0].get("error") != "cancelled"
        or not isinstance(finished[-1], dict)
        or finished[-1].get("error") != "cancelled"
    ):
        raise SystemExit(
            f"orphan active: begun={begun!r} finished={finished!r} active={active_finished!r} body={active_body!r}"
        )
    bad_root = caller.admit(topic="bad", payload={}, from_="orphan")
    for _ in range(8):
        runtime.advance()
    bad_cancelled = caller.cancel(bad_root.header.id)
    try:
        for _ in range(8):
            runtime.advance()
    except Exception as error:
        raise SystemExit(f"orphan bad hook escaped: {error}") from error
    stats = runtime.stats()
    if (
        not bad_cancelled
        or stats["cancel_errors"] != 1
        or stats["last_cancel_error"] != "cleanup boom"
    ):
        raise SystemExit(f"orphan bad hook: {stats!r}")

    bad_core = core_of(bad_host)
    original_cancel = bad_core.book.cancel
    lease_calls = 0
    def lease_once(owner):
        nonlocal lease_calls
        lease_calls += 1
        if lease_calls == 1:
            raise LeasePending()
        return original_cancel(owner)
    bad_core.book.cancel = lease_once
    lease_root = caller.admit(topic="bad", payload={}, from_="orphan")
    for _ in range(8):
        runtime.advance()
    lease_cancelled = caller.cancel(lease_root.header.id)
    for _ in range(12):
        runtime.advance()
    lease_stats = runtime.stats()
    bad_core.book.cancel = original_cancel
    if (
        not lease_cancelled
        or lease_calls != 2
        or bad_core.jobs
        or lease_stats["pending_cancels"] != 0
        or lease_stats["active"] != 0
    ):
        raise SystemExit(f"orphan lease: {lease_stats!r} calls={lease_calls}")

    pay_root = caller.admit(topic="orphan.work", payload={"n": 5}, from_="orphan")
    for _ in range(4):
        runtime.advance()
    def pay_boom(_completion):
        raise RuntimeError("pay boom")
    pay_root.payload.pay = pay_boom
    try:
        caller.cancel(pay_root.header.id)
    except RuntimeError as error:
        if str(error) != "pay boom":
            raise
    else:
        raise SystemExit("orphan pay: expected an exception")
    if runtime.stats()["active"] != 1:
        raise SystemExit(f"orphan pay caller leaked: {runtime.stats()!r}")
    for _ in range(4):
        runtime.advance()
    if runtime.stats()["active"] != 0:
        raise SystemExit(f"orphan pay holder leaked: {runtime.stats()!r}")
    print("orphan ok")


if __name__ == "__main__":
    main()
