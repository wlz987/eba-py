from eba import Bus, ManualClock, Runtime, SeqIdGen


def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    runtime.close()
    try:
        runtime.advance()
    except RuntimeError as error:
        print("refused:", error)
        return
    raise SystemExit("advance after close should be refused")


if __name__ == "__main__":
    main()
