from eba import Inbox, Job, JobHost


class SilentJob(Job):
    def begin(self, ctx) -> None:
        pass


class SilentHost(JobHost):
    def make_job(self, root):
        return SilentJob(root)


def main() -> None:
    try:
        SilentHost(actor_id="x", receiver=Inbox(8).receiver(), patterns=[], active_limit=0)
    except ValueError as error:
        print("refused:", error)
        return
    raise SystemExit("zero active limit should be refused")


if __name__ == "__main__":
    main()
