import asyncio

from eba import Bus, Caller, Drive, Inbox, ManualClock, Runtime, SeqIdGen


async def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    caller = Caller(Inbox(8).receiver(), runtime.id_gen)
    async with Drive(runtime) as drive:
        pending = drive.open(caller, topic="cancel.work", payload={"n": 1}, from_="cancel")
        cancelled = caller.cancel(pending.envelope.header.id)
        completion = await pending.ready
        body = completion.body
        if not cancelled or not isinstance(body, dict) or body.get("error") != "cancelled":
            raise SystemExit(f"expected cancelled, got {cancelled} {body!r}")
        print("cancelled:", cancelled, body["error"])


if __name__ == "__main__":
    asyncio.run(main())
