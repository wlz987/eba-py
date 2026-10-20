from eba import Bus, Inbox


def main() -> None:
    sub = Bus().subscribe("a.b", Inbox(8))
    first = sub.close()
    second = sub.close()
    if not first or second:
        raise SystemExit(f"subclose leaked: {first}/{second}")
    print("subclose:", first, second)


if __name__ == "__main__":
    main()
