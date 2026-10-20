from eba import Inbox


def main() -> None:
    try:
        Inbox(0)
    except ValueError as error:
        print("refused:", error)
        return
    raise SystemExit("zero capacity should be refused")


if __name__ == "__main__":
    main()
