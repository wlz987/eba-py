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
    first = runtime.close("a")
    if first or a.state != "closed" or b.state != "running":
        raise SystemExit(f"selective close leaked: {len(first)}/{a.state}/{b.state}")
    second = runtime.close()
    if second or b.state != "closed":
        raise SystemExit(f"rest close leaked: {len(second)}/{b.state}")
    print("selective:", len(first), len(second))


if __name__ == "__main__":
    main()
