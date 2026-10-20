from eba import Inbox, Job, JobHost


class SilentJob(Job):
    def begin(self, ctx) -> None:
        pass


class SilentHost(JobHost):
    def make_job(self, root):
        return SilentJob(root)


def main() -> None:
    receiver = Inbox(8).receiver()
    SilentHost(actor_id="a", receiver=receiver, patterns=[])
    try:
        SilentHost(actor_id="b", receiver=receiver, patterns=[])
    except RuntimeError as error:
        print("refused:", error)
        return
    raise SystemExit("second receiver should be refused")


if __name__ == "__main__":
    main()
