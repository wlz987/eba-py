from eba import Bus, make_envelope


def main() -> None:
    envelope = make_envelope(topic="x.y", payload=1, from_="c", id="e1")
    delivered = Bus().publish(envelope)
    if delivered is not False:
        raise SystemExit(f"noroute leaked: {delivered}")
    print("noroute:", delivered)


if __name__ == "__main__":
    main()
