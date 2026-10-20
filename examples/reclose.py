from eba import Bus, ManualClock, Runtime, SeqIdGen


def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    first = runtime.close()
    second = runtime.close()
    if first or second:
        raise SystemExit(f"expected two empty closes, got {len(first)}/{len(second)}")
    print("reclose:", len(first), len(second))


if __name__ == "__main__":
    main()
