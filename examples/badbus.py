from eba import Bus, Inbox
from eba.errors import InvalidTopic


def main() -> None:
    try:
        Bus().subscribe("bad!", Inbox(8))
    except InvalidTopic as error:
        print("refused:", error)
        return
    raise SystemExit("bad pattern should be refused by the bus")


if __name__ == "__main__":
    main()
