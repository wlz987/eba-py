from eba import Bus, Inbox


def main() -> None:
    bus = Bus()
    inbox = Inbox(8)
    first = bus.subscribe("a.b", inbox)
    second = bus.subscribe("a.b", inbox)
    closed_first = first.close()
    closed_second = second.close()
    if not closed_first or not closed_second or first.active() or second.active():
        raise SystemExit(f"subdup leaked: {closed_first}/{closed_second}")
    print("subdup:", closed_first, closed_second, first.active(), second.active())


if __name__ == "__main__":
    main()
