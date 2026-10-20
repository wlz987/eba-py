from eba import Bus, Inbox


def main() -> None:
    sub = Bus().subscribe("a.b", Inbox(8))
    sub.disarm()
    active = sub.active()
    closed = sub.close()
    if active or closed:
        raise SystemExit(f"subdisarm leaked: {active}/{closed}")
    print("subdisarm:", active, closed)


if __name__ == "__main__":
    main()
