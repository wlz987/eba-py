from eba import Bus, ManualClock, Runtime, SeqIdGen


def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    try:
        runtime.close("nobody")
    except RuntimeError as error:
        print("refused:", error)
        return
    raise SystemExit("unknown host should be refused")


if __name__ == "__main__":
    main()
