import asyncio
import time

from eba import (
    Bus,
    Inbox,
    Job,
    JobHost,
    ManualClock,
    Runtime,
    SeqIdGen,
    ok_payload,
)
from eba.job import Caller
from eba.runtime.drive import Drive


class EchoJob(Job):
    def begin(self, ctx) -> None:
        ctx.finish(ok_payload({"n": ctx.root.payload["n"]}))


class EchoHost(JobHost):
    def make_job(self, root):
        return EchoJob(root)


async def main() -> None:
    bus = Bus()
    runtime = Runtime(bus, ManualClock(), SeqIdGen())
    runtime.add(EchoHost(actor_id="echo", receiver=Inbox(64).receiver(), patterns=["echo.work"]))
    caller = Caller(Inbox(64).receiver(), runtime.id_gen)
    async with Drive(runtime) as drive:
        for _ in range(50):
            warm = drive.open(caller, topic="echo.work", payload={"n": 0}, from_="bench")
            await warm.ready
        total = 5000
        window = 64
        start = time.perf_counter()
        done = 0
        while done < total:
            batch = min(window, total - done)
            pending = [
                drive.open(caller, topic="echo.work", payload={"n": done + i}, from_="bench") for i in range(batch)
            ]
            await asyncio.gather(*(item.ready for item in pending))
            done += batch
        elapsed = time.perf_counter() - start
    print(f"{total} messages in {elapsed:.3f}s = {total / elapsed:.0f} msg/s")


if __name__ == "__main__":
    asyncio.run(main())
