"""Run with:  python3 test_logic.py   (no GUI needed)"""
import random
from queue_logic import LinearQueue, CircularQueue, Deque, PriorityQueue


def run(q, op, *a):
    steps, val = q.run(op, *a)
    assert steps, "operation yielded no steps"
    for s in steps:  # every highlighted pseudocode line must exist
        assert 0 <= s.line < len(q.PSEUDO[op]), (op, s.line)
    return steps, val


def test_linear_slides():
    q = LinearQueue(3)
    steps, v = run(q, "dequeue")
    assert v is None and any(s.kind == "err" for s in steps)                           # underflow
    for v in (10, 20, 30):
        run(q, "enqueue", v)
    assert (q.front, q.rear) == (0, 2)
    steps, v = run(q, "enqueue", 40)
    assert v is None and any(s.kind == "err" for s in steps)                           # overflow
    assert run(q, "peek")[1] == 10
    assert run(q, "display")[1] == [10, 20, 30]
    assert run(q, "dequeue")[1] == 10 and (q.front, q.rear) == (1, 2)
    # wasted space: one slot free at front, yet still overflow
    assert run(q, "enqueue", 99)[1] is None
    run(q, "dequeue"); run(q, "dequeue")
    assert (q.front, q.rear) == (-1, -1)                                               # optional reset


def test_linear_no_reset():
    q = LinearQueue(2, reset_on_empty=False)
    run(q, "enqueue", 1); run(q, "enqueue", 2); run(q, "dequeue"); run(q, "dequeue")
    assert q.front > q.rear and q.size == 0
    assert run(q, "enqueue", 3)[1] is None          # full forever -> the classic weakness
    assert run(q, "peek")[1] is None                # front > rear counts as empty


def test_circular_wrap():
    q = CircularQueue(4)
    for v in range(4):
        run(q, "enqueue", v)
    assert run(q, "enqueue", 9)[1] is None
    run(q, "dequeue"); run(q, "dequeue")
    run(q, "enqueue", 7)
    assert q.rear == 0 and run(q, "display")[1] == [2, 3, 7]


def test_circular_random_vs_reference():
    rng = random.Random(1)
    for cap in (1, 2, 5, 8):
        q, ref = CircularQueue(cap), []
        for _ in range(500):
            if rng.random() < .55:
                v = rng.randint(0, 99)
                ok = run(q, "enqueue", v)[1] is not None
                if len(ref) < cap:
                    ref.append(v); assert ok
                else:
                    assert not ok
            else:
                got = run(q, "dequeue")[1]
                assert got == (ref.pop(0) if ref else None)
            assert run(q, "display")[1] == ref


def test_deque_random_vs_reference():
    rng = random.Random(2)
    for cap in (1, 3, 6):
        q, ref = Deque(cap), []
        for _ in range(800):
            op = rng.choice(["insert_front", "insert_rear", "delete_front", "delete_rear"])
            if op.startswith("insert"):
                v = rng.randint(0, 99)
                ok = run(q, op, v)[1] is not None
                if len(ref) < cap:
                    ref.insert(0, v) if op == "insert_front" else ref.append(v); assert ok
                else:
                    assert not ok
            else:
                got = run(q, op)[1]
                exp = (ref.pop(0) if op == "delete_front" else ref.pop()) if ref else None
                assert got == exp
            assert run(q, "display")[1] == ref
            assert run(q, "peek_front")[1] == (ref[0] if ref else None)
            assert run(q, "peek_rear")[1] == (ref[-1] if ref else None)


def test_priority():
    q = PriorityQueue(5)
    for v, p in [("a", 3), ("b", 1), ("c", 2), ("d", 2), ("e", 5)]:
        run(q, "enqueue", v, p)
    assert run(q, "enqueue", "f", 1)[1] is None                       # full
    assert [run(q, "dequeue")[1] for _ in range(5)] == ["b", "c", "d", "a", "e"]  # stable FIFO ties
    assert run(q, "dequeue")[1] is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)
