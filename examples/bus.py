from eba import Bus, Inbox, MailboxFull, make_envelope
from eba.envelope.errors import EnvelopeBuildError
from eba.mail.inbox import pause_work, watch_space
from eba.notify.signal import Signal
from eba.notify.watch import Interest


def letter(topic: str, id: str):
    return make_envelope(topic=topic, payload={"sku": "sold-out"}, from_="order", id=id)


def main() -> None:
    bus = Bus()
    inventory, audit, overview = Inbox(1), Inbox(4), Inbox(4)
    boxes = {
        "库存": inventory.receiver(),
        "旁听": audit.receiver(),
        "总览": overview.receiver(),
    }
    bus.subscribe("inventory.*", inventory)
    bus.subscribe("inventory.reserve", audit)
    bus.subscribe("inventory.**", overview)

    def take() -> list[tuple[str, str]]:
        found = []
        for name, receiver in boxes.items():
            item = receiver.try_recv()
            if item is not None:
                found.append((name, item.header.id))
        return found

    bus.publish(letter("inventory.reserve", "child-42"))
    print("inventory.reserve", take())
    bus.publish(letter("inventory.reserve.extra", "child-43"))
    print("inventory.reserve.extra", take())
    bus.publish(letter("inventory.reserve", "child-44"))
    try:
        bus.publish(letter("inventory.reserve", "child-45"))
    except MailboxFull:
        print("库存已满", take())

    full, room = Inbox(1), Inbox(4)
    full_side, room_side = full.receiver(), room.receiver()
    bus.subscribe("effort.x", full)
    bus.subscribe("effort.*", room)
    bus.publish(letter("effort.x", "e1"))
    room_side.try_recv()
    skipped = bus.publish_best_effort(letter("effort.x", "e2"))
    left, right = full_side.try_recv(), room_side.try_recv()
    assert left is not None and right is not None
    print("best-effort", skipped, left.header.id, right.header.id)

    latest = Inbox(4)
    latest_side = latest.receiver()
    bus.subscribe("latest.x", latest)
    bus.publish(letter("latest.x", "l1"))
    bus.publish(letter("latest.x", "l2"))
    stale = bus.publish_latest(letter("latest.x", "l3"))
    kept = latest_side.try_recv()
    assert stale == 0 and kept is not None and kept.header.id == "l3"
    assert latest_side.try_recv() is None

    try:
        bus.publish_latest(
            make_envelope(
                topic="latest.x",
                payload=1,
                from_="x",
                id="req-1",
                kind="request",
                reply_to="sys.reply.i1",
            )
        )
    except EnvelopeBuildError:
        pass
    else:
        raise SystemExit("publish_latest accepted a request")

    busy = Inbox(1)
    busy_side = busy.receiver()
    bus.subscribe("latest.y.*", busy)
    bus.publish(letter("latest.y.a", "y1"))
    assert bus.publish_latest(letter("latest.y.a", "y2")) == 0
    kept = busy_side.try_recv()
    assert kept is not None and kept.header.id == "y2"
    bus.publish(letter("latest.y.a", "y3"))
    assert bus.publish_latest(letter("latest.y.b", "y4")) == 1
    kept = busy_side.try_recv()
    assert kept is not None and kept.header.id == "y3"

    paused = Inbox(2)
    paused_side = paused.receiver()
    bus.subscribe("latest.p", paused)
    bus.publish(letter("latest.p", "p1"))
    pause_work(paused, True)
    assert bus.publish_latest(letter("latest.p", "p2")) == 1
    pause_work(paused, False)
    assert bus.publish_latest(letter("latest.p", "p3")) == 0
    kept = paused_side.try_recv()
    assert kept is not None and kept.header.id == "p3"

    candidates = {}
    watched = Inbox(2)
    bus.subscribe("latest.w", watched)
    interest = Interest(Signal(), candidates, "latest.w")
    watch_space(watched, interest)
    bus.publish(letter("latest.w", "w1"))
    bus.publish(letter("latest.w", "w2"))
    assert bus.publish_latest(letter("latest.w", "w3")) == 0
    assert "latest.w" in candidates
    print("latest ok")


if __name__ == "__main__":
    main()
