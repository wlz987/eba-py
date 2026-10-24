from eba import Reply, ok_payload
from eba.park import Park


def main() -> None:
    park: Park[str, int] = Park()

    first, second = Reply(), Reply()
    assert park.wait("k", first) is None
    assert park.wait("k", second) is None
    assert park.wake("k", 7) is first
    assert park.wake("k", 8) is second
    assert park.wake("k", 9) is None

    credit = Reply()
    assert park.wait("k", credit) == 9
    credit.send(ok_payload(9))

    left, right = Reply(), Reply()
    assert park.wait("move", left) is None
    assert park.wait("move", right) is None
    assert park.requeue("move", "next", 1, 1) == [left]
    assert park.wake("next", 1) is right

    late = Reply()
    assert park.wait("deadline", late, 5) is None
    assert park.expire(4) == []
    assert park.expire(5) == [late]

    lost, found = Reply(), Reply()
    assert park.wait("cancel", lost) is None
    assert park.wait("cancel", found) is None
    assert park.cancel("cancel") == [lost, found]

    owner_a, owner_b = Reply(), Reply()
    assert park.wait("own", owner_a, owner=1) is None
    assert park.wait("own", owner_b, owner=2) is None
    assert park.cancel_owner(1) == [owner_a]
    assert park.wake("own", 1) is owner_b
    assert park.keys() == []

    capped: Park[str, int] = Park()
    for value in range(4097):
        capped.wake("cap", value)
    for value in range(4096):
        assert capped.wait("cap", Reply()) == value
    assert capped.wait("cap", Reply()) is None

    print("park ok")


if __name__ == "__main__":
    main()
