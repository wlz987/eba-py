from eba import Inbox


def main() -> None:
    inbox = Inbox(8)
    receiver = inbox.receiver()
    first = receiver.close()
    second = receiver.close()
    if not first or second or not inbox.is_closed:
        raise SystemExit(f"receiverclose leaked: {first}/{second}/{inbox.is_closed}")
    print("receiverclose:", first, second, inbox.is_closed)


if __name__ == "__main__":
    main()
