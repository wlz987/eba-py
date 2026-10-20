from eba import Bus, Caller, Inbox, ManualClock, Runtime, SeqIdGen
from eba.envelope.errors import EnvelopeBuildError


def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    caller = Caller(Inbox(4).receiver(), runtime.id_gen)
    runtime.add(caller)
    try:
        caller.admit(topic="bad!", payload={"n": 1}, from_="bad")
    except EnvelopeBuildError as error:
        print("refused:", error)
        return
    raise SystemExit("bad topic should be refused")


if __name__ == "__main__":
    main()
