from eba import Bus, Inbox, Job, JobHost, ManualClock, Runtime, SeqIdGen


class SilentJob(Job):
    def begin(self, ctx) -> None:
        pass


class SilentHost(JobHost):
    def make_job(self, root):
        return SilentJob(root)


def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    a = SilentHost(actor_id="a", receiver=Inbox(8).receiver(), patterns=[])
    b = SilentHost(actor_id="b", receiver=Inbox(8).receiver(), patterns=[])
    runtime.add(a)
    runtime.add(b)
    runtime.shutdown("a")
    if a.state != "draining" or b.state != "running":
        raise SystemExit(f"selective drain leaked: {a.state}/{b.state}")
    runtime.close()
    print("drain:", a.state, b.state)


if __name__ == "__main__":
    main()
