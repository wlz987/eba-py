from eba import Bus, Inbox, Job, JobHost, ManualClock, Runtime, SeqIdGen


class SilentJob(Job):
    def begin(self, ctx) -> None:
        pass


class SilentHost(JobHost):
    def make_job(self, root):
        return SilentJob(root)


def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    runtime.add(SilentHost(actor_id="same", receiver=Inbox(8).receiver(), patterns=[]))
    try:
        runtime.add(SilentHost(actor_id="same", receiver=Inbox(8).receiver(), patterns=[]))
    except RuntimeError as error:
        print("refused:", error)
        return
    raise SystemExit("duplicate host should be refused")


if __name__ == "__main__":
    main()
