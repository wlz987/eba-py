import asyncio

from eba import Bus, Caller, Drive, Inbox, Job, JobHost, ManualClock, Runtime, SeqIdGen


class SilentJob(Job):
    def begin(self, ctx) -> None:
        pass


class SilentHost(JobHost):
    def make_job(self, root):
        return SilentJob(root)


async def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    runtime.add(SilentHost(actor_id="silent", receiver=Inbox(8).receiver(), patterns=["silent.work"]))
    caller = Caller(Inbox(8).receiver(), runtime.id_gen)
    async with Drive(runtime) as drive:
        pending = drive.open(caller, topic="silent.work", payload={"n": 1}, from_="silent")
        completion = await pending.ready
        body = completion.body
        if not isinstance(body, dict) or body.get("error") != "job_silent":
            raise SystemExit(f"expected job_silent, got {body!r}")
        print("silent:", body["error"])


if __name__ == "__main__":
    asyncio.run(main())
