from eba import Bus, Inbox, Job, JobHost, ManualClock, Runtime, SeqIdGen, ok_payload


class Echo(Job):
    def begin(self, ctx) -> None:
        ctx.reply(ok_payload(ctx.root.payload["value"]))


class EchoHost(JobHost):
    def make_job(self, root):
        return Echo(root)


class Hold(Job):
    def begin(self, ctx) -> None:
        ctx.hold()


class HoldHost(JobHost):
    def make_job(self, root):
        return Hold(root)


def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    runtime.add(EchoHost(actor_id="echo", receiver=Inbox(32).receiver(), patterns=["echo"]))
    runtime.add(HoldHost(actor_id="hold", receiver=Inbox(8).receiver(), patterns=["hold"]))
    seen = []
    runtime.ask_with("echo", {"value": 7}, from_="handoff", pay=seen.append)
    for _ in range(12):
        runtime.advance()
    if len(seen) != 1 or seen[0].body != {"ok": True, "value": 7}:
        raise SystemExit(f"handoff: {seen!r}")

    batch = []
    for value in range(9):
        runtime.ask_with("echo", {"value": value}, from_="handoff", pay=batch.append)
    for _ in range(24):
        runtime.advance()
    values = sorted(
        completion.body["value"]
        for completion in batch
        if completion.body is not None
    )
    if len(batch) != 9 or values != list(range(9)):
        raise SystemExit(f"handoff batch: {batch!r}")

    closed = []
    runtime.ask_with("hold", {"n": 0}, from_="handoff", pay=closed.append)
    for _ in range(4):
        runtime.advance()
    runtime.close()
    if len(closed) != 1 or not isinstance(closed[0].body, dict) or closed[0].body.get("error") != "host_draining":
        raise SystemExit(f"handoff close: {closed!r}")
    print("handoff ok")


if __name__ == "__main__":
    main()
