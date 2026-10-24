from eba import Bus, Inbox, ManualClock, Runtime, SeqIdGen
from eba.errors import MailboxFull
from eba.job import Caller


def main() -> None:
    runtime = Runtime(Bus(), ManualClock(), SeqIdGen())
    caller = Caller(Inbox(1).receiver(), runtime.id_gen)
    runtime.add(caller)
    caller.admit(topic="full.work", payload={"n": 1}, from_="full")
    try:
        caller.admit(topic="full.work", payload={"n": 2}, from_="full")
    except MailboxFull as error:
        print("refused:", error)
        return
    raise SystemExit("second admit should be refused")


if __name__ == "__main__":
    main()
