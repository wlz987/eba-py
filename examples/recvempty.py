from eba import Inbox


def main() -> None:
    receiver = Inbox(8).receiver()
    received = receiver.try_recv()
    if received is not None:
        raise SystemExit(f"recvempty leaked: {received}")
    print("recvempty:", received)


if __name__ == "__main__":
    main()
