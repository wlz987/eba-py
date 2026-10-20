from eba import Bus, Inbox, make_envelope


def main() -> None:
    bus = Bus()
    inbox = Inbox(8)
    receiver = inbox.receiver()
    bus.subscribe("a.b", inbox)
    receiver.close()
    envelope = make_envelope(topic="a.b", payload=1, from_="c", id="e1")
    delivered = bus.publish(envelope)
    if delivered is not False:
        raise SystemExit(f"publishclosed leaked: {delivered}")
    print("publishclosed:", delivered)


if __name__ == "__main__":
    main()
