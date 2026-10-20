from eba import Bus, Caller, Inbox, ManualClock, Runtime, SeqIdGen
from eba.errors import BackpressureError


def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    caller = Caller(Inbox(8).receiver(), runtime.id_gen, active_limit=1)
    runtime.add(caller)
    caller.admit(topic="bp.work", payload={"n": 1}, from_="bp")
    try:
        caller.admit(topic="bp.work", payload={"n": 2}, from_="bp")
    except BackpressureError as error:
        print("refused:", error)
        return
    raise SystemExit("second admit should be backpressured")


if __name__ == "__main__":
    main()
