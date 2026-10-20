from eba import Bus, Inbox, MailboxFull, make_envelope


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


if __name__ == "__main__":
    main()
