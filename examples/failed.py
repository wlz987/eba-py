import asyncio

from eba import Bus, Caller, Drive, Inbox, Job, JobHost, ManualClock, Runtime, SeqIdGen


class FailJob(Job):
    def begin(self, ctx) -> None:
        raise ValueError("boom")


class FailHost(JobHost):
    def make_job(self, root):
        return FailJob(root)


async def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    runtime.add(FailHost(actor_id="fail", receiver=Inbox(8).receiver(), patterns=["fail.work"]))
    caller = Caller(Inbox(8).receiver(), runtime.id_gen)
    async with Drive(runtime) as drive:
        pending = drive.open(caller, topic="fail.work", payload={"n": 1}, from_="fail")
        completion = await pending.ready
        body = completion.body
        if not isinstance(body, dict) or body.get("error") != "job_failed":
            raise SystemExit(f"expected job_failed, got {body!r}")
        print("failed:", body["error"], body.get("message"))


if __name__ == "__main__":
    asyncio.run(main())
