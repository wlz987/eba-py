from eba import Bus, Inbox, ManualClock, Runtime, SeqIdGen
from eba.job import Caller


def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    caller = Caller(Inbox(4).receiver(), runtime.id_gen)
    runtime.add(caller)
    runtime.close()
    try:
        caller.admit(topic="closed.work", payload={"n": 1}, from_="closed")
    except RuntimeError as error:
        print("refused:", error)
        return
    raise SystemExit("admit after close should be refused")


if __name__ == "__main__":
    main()
