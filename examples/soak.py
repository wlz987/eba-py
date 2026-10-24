"""Cancellation/error soak: every hold/bad request is cancelled; stats must return to zero."""

import contextlib
import random

from eba import Bus, Inbox, Job, JobHost, ManualClock, Runtime, SeqIdGen, ok_payload
from eba.job import Caller


class Echo(Job):
    def begin(self, ctx):
        ctx.reply(ok_payload({"n": 1}))


class Hold(Job):
    def begin(self, ctx):
        ctx.hold()


class Bad(Job):
    def begin(self, ctx):
        ctx.request(stage="inner", topic="hold", payload={})

    def on_finished(self, body):
        raise RuntimeError("cleanup")


class EchoHost(JobHost):
    def make_job(self, root):
        return Echo(root)


class HoldHost(JobHost):
    def make_job(self, root):
        return Hold(root)


class BadHost(JobHost):
    def make_job(self, root):
        return Bad(root)


def pay_boom(_completion):
    raise RuntimeError("pay")


def main() -> None:
    random.seed(7)
    cancel_errors = 0
    for wave in range(100):
        runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
        runtime.add(EchoHost(actor_id="echo", receiver=Inbox(64).receiver(), patterns=["echo"]))
        runtime.add(HoldHost(actor_id="hold", receiver=Inbox(64).receiver(), patterns=["hold"]))
        runtime.add(BadHost(actor_id="bad", receiver=Inbox(64).receiver(), patterns=["bad"]))
        caller = Caller(Inbox(256).receiver(), runtime.id_gen)
        runtime.add(caller)
        roots = []
        for index in range(20):
            topic = random.choice(("echo", "hold", "bad"))
            roots.append((topic, caller.admit(topic=topic, payload={"n": index}, from_="soak")))
        for _ in range(3):
            runtime.advance()
        for topic, root in roots:
            if topic == "echo":
                continue
            if random.random() < 0.25:
                root.payload.pay = pay_boom
            with contextlib.suppress(RuntimeError):
                caller.cancel(root.header.id)
        for _ in range(12):
            runtime.advance()
        stats = runtime.stats()
        if stats["active"] or stats["held"] or stats["pending"] or stats["queued"]:
            raise SystemExit(f"soak leak wave {wave}: {stats}")
        cancel_errors += stats["cancel_errors"]
        runtime.close()
    if cancel_errors == 0:
        raise SystemExit("soak did not exercise cancel_errors")
    print(f"soak ok: 100 waves x 20 asks, {cancel_errors} contained hook errors")


if __name__ == "__main__":
    main()
