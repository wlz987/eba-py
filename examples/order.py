import asyncio

from eba import (
    Bus,
    Caller,
    Drive,
    Inbox,
    Job,
    JobHost,
    ManualClock,
    Runtime,
    SeqIdGen,
    err_payload,
    is_result_ok,
    ok_payload,
    result_error,
)


class OrderJob(Job):
    def begin(self, ctx) -> None:
        ctx.request(stage="inventory", topic="inventory.reserve", payload=ctx.root.payload)

    def on_stage_result(self, ctx, stage, completion) -> None:
        if completion.body is None or not is_result_ok(completion.body):
            ctx.finish(completion.body or err_payload("dependency_timeout", {"stage": stage}))
            return
        if stage == "inventory":
            ctx.request(stage="payment", topic="payment.charge", payload=ctx.root.payload)
            return
        ctx.finish(ok_payload({"sku": ctx.root.payload["sku"]}))


class ServiceJob(Job):
    def begin(self, ctx) -> None:
        sku = ctx.root.payload["sku"]
        if ctx.root.header.topic == "inventory.reserve" and sku == "sold-out":
            ctx.finish(err_payload("out_of_stock"))
            return
        if ctx.root.header.topic == "inventory.reserve":
            ctx.finish(ok_payload("reserved"))
            return
        ctx.finish(ok_payload("paid"))


class Orders(JobHost):
    def make_job(self, root):
        return OrderJob(root)


class Services(JobHost):
    def make_job(self, root):
        return ServiceJob(root)


async def main() -> None:
    bus = Bus()
    runtime = Runtime(bus, ManualClock(), SeqIdGen())
    runtime.add(Orders(actor_id="orders", receiver=Inbox(8).receiver(), patterns=["order.submit"]))
    runtime.add(
        Services(
            actor_id="services",
            receiver=Inbox(8).receiver(),
            patterns=["inventory.reserve", "payment.charge"],
        )
    )
    caller = Caller(Inbox(8).receiver(), runtime.id_gen)
    async with Drive(runtime) as drive:
        first = drive.open(caller, topic="order.submit", payload={"sku": "A"}, from_="caller.a")
        second = drive.open(caller, topic="order.submit", payload={"sku": "sold-out"}, from_="caller.b")
        print("收信已返回", first.envelope.header.id, second.envelope.header.id)
        left, right = await asyncio.gather(first.ready, second.ready)
    print("甲", left.body)
    print("乙", result_error(right.body))


if __name__ == "__main__":
    asyncio.run(main())
