"""
queue_logic.py - the data-structure side of the Queue Simulator (no GUI here).

Every operation is a *generator*: it mutates the queue and yields a Step after each
line of pseudocode it "executes". A Step carries the pseudocode line number, an
explanation, and a snapshot of the queue. The GUI simply replays those steps.

The Simple Queue follows the course slides exactly (front = rear = -1, Overflow when
rear == size - 1, Underflow when front == -1 OR front > rear, optional reset).
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Step:
    line: int                 # index into PSEUDO[op]
    msg: str                  # plain-English explanation of what just happened
    kind: str                 # 'info' | 'ok' | 'err' | 'cmp'
    snap: dict                # state after this step
    event: Optional[tuple] = None   # ('write', i) ('remove', i, v) ('shift', a, b) ...
    hl: frozenset = frozenset()     # indices to highlight


class BaseQueue:
    TITLE = ""
    PSEUDO: dict = {}

    def __init__(self, cap=6):
        self.cap = cap
        self.reset()

    # ---- helpers -------------------------------------------------------
    def snapshot(self):
        return {"cells": list(self.cells), "front": self.front, "rear": self.rear,
                "live": frozenset(self.live()), "cap": self.cap}

    def _s(self, line, msg, kind="info", event=None, hl=()):
        return Step(line, msg, kind, self.snapshot(), event, frozenset(hl))

    @property
    def size(self):
        return len(self.live())

    def run(self, op, *args):
        """Run an operation to completion -> (list of Steps, return value)."""
        steps, gen = [], getattr(self, op)(*args)
        try:
            while True:
                steps.append(next(gen))
        except StopIteration as stop:
            return steps, stop.value

    # ---- one-line operations shared by all queues ----------------------
    def is_empty(self):
        yield self._s(0, f"isEmpty() -> {self.size == 0}", "ok")
        return self.size == 0

    def is_full(self):
        yield self._s(0, f"isFull() -> {self._full()}", "ok")
        return self._full()


# ======================================================================
# 1. Simple (linear) queue - exactly the algorithms from the slides
# ======================================================================
class LinearQueue(BaseQueue):
    TITLE = "Simple Queue"
    PSEUDO = {
        "enqueue": ["START", "if rear == size - 1:", '    print "Overflow"; EXIT',
                    "rear = rear + 1", "if front == -1: front = 0",
                    "queue[rear] = value", "return success", "END"],
        "dequeue": ["START", "if front == -1 OR front > rear:", '    print "Underflow"; EXIT',
                    "value = queue[front]", "front = front + 1",
                    "if front > rear: front = rear = -1   # optional reset",
                    "return value", "END"],
        "peek": ["START", 'if front == -1 OR front > rear: return "Queue is empty"',
                 "return queue[front]", "END"],
        "display": ["START", "if front == -1 OR front > rear:", '    print "Queue is empty"; EXIT',
                    "else:", "    for i from front to rear:", "        print queue[i]", "END"],
        "is_empty": ["return front == -1 OR front > rear"],
        "is_full": ["return rear == size - 1"],
    }

    def __init__(self, cap=6, reset_on_empty=True):
        self.reset_on_empty = reset_on_empty
        super().__init__(cap)

    def reset(self):
        self.cells = [None] * self.cap
        self.front = self.rear = -1

    def live(self):
        return set() if self.front == -1 else set(range(self.front, self.rear + 1))

    def _empty(self):
        return self.front == -1 or self.front > self.rear

    def _full(self):
        return self.rear == self.cap - 1

    @property
    def wasted(self):
        """Slots in front of `front` that can never be reused (linear-queue weakness)."""
        if self.front == -1:
            return 0
        return self.front

    def enqueue(self, v):
        yield self._s(0, f"enqueue({v}) started.")
        full = self._full()
        yield self._s(1, f"Is rear == size - 1 ?  {self.rear} == {self.cap - 1}  ->  {full}",
                      "cmp", event=("compare", self.rear), hl=[self.rear] if self.rear >= 0 else [])
        if full:
            extra = ""
            if self.front > 0:
                extra = (f"  Note: {self.front} slot(s) at the front are free but wasted - "
                         "this is why the Circular Queue exists.")
            yield self._s(2, "OVERFLOW - the queue is full, nothing inserted." + extra, "err")
            yield self._s(7, "END")
            return None
        self.rear += 1
        yield self._s(3, f"rear = rear + 1  ->  rear = {self.rear}", hl=[self.rear])
        if self.front == -1:
            self.front = 0
            yield self._s(4, "front was -1 (first element) so front = 0", hl=[0])
        else:
            yield self._s(4, f"front is already {self.front}, so it stays unchanged")
        self.cells[self.rear] = (v, None)
        yield self._s(5, f"queue[{self.rear}] = {v}", event=("write", self.rear), hl=[self.rear])
        yield self._s(6, f"Success - {v} inserted at REAR.", "ok")
        yield self._s(7, "END")
        return v

    def dequeue(self):
        yield self._s(0, "dequeue() started.")
        empty = self._empty()
        yield self._s(1, f"Is front == -1 OR front > rear ?  ({self.front}, {self.rear})  ->  {empty}", "cmp")
        if empty:
            yield self._s(2, "UNDERFLOW - the queue is empty, nothing to remove.", "err")
            yield self._s(7, "END")
            return None
        v = self.cells[self.front][0]
        yield self._s(3, f"value = queue[{self.front}] = {v}", hl=[self.front])
        old = self.front
        self.front += 1
        yield self._s(4, f"front = front + 1  ->  front = {self.front}", event=("remove", old, v))
        if self.front > self.rear:
            if self.reset_on_empty:
                self.front = self.rear = -1
                self.cells = [None] * self.cap
                yield self._s(5, "front > rear: queue is now empty, so reset front = rear = -1 "
                                 "(all slots reusable).")
            else:
                yield self._s(5, "front > rear: queue is empty, but with the optional reset OFF "
                                 f"rear stays at {self.rear} - those slots are wasted.")
        else:
            yield self._s(5, f"front <= rear ({self.front} <= {self.rear}): queue not empty yet.")
        yield self._s(6, f"Success - removed {v} from FRONT.", "ok")
        yield self._s(7, "END")
        return v

    def peek(self):
        yield self._s(0, "peek() started.")
        if self._empty():
            yield self._s(1, "Queue is empty - nothing to peek.", "err")
            yield self._s(3, "END")
            return None
        v = self.cells[self.front][0]
        yield self._s(2, f"Front element is {v} (queue[{self.front}]). Queue is not changed.",
                      "ok", hl=[self.front])
        yield self._s(3, "END")
        return v

    def display(self):
        yield self._s(0, "display() started.")
        if self._empty():
            yield self._s(1, "front == -1 OR front > rear -> true", "cmp")
            yield self._s(2, "Queue is empty", "err")
            yield self._s(6, "END")
            return []
        yield self._s(1, "Queue is not empty, so we walk from front to rear.", "cmp")
        yield self._s(3, "else:")
        out = []
        for i in range(self.front, self.rear + 1):
            yield self._s(4, f"i = {i}", hl=[i])
            out.append(self.cells[i][0])
            yield self._s(5, f"print queue[{i}] = {self.cells[i][0]}     (printed so far: {out})",
                          hl=[i])
        yield self._s(6, f"Queue (front -> rear): {out}", "ok")
        return out


# ======================================================================
# 2. Circular queue (and base for the deque)
# ======================================================================
class RingQueue(BaseQueue):
    def reset(self):
        self.cells = [None] * self.cap
        self.front = self.rear = -1

    def live(self):
        if self.front == -1:
            return set()
        n = (self.rear - self.front) % self.cap + 1
        return {(self.front + k) % self.cap for k in range(n)}

    def _empty(self):
        return self.front == -1

    def _full(self):
        return (self.rear + 1) % self.cap == self.front

    # -- insert at rear (circular enqueue / deque insertRear) --
    def enqueue(self, v):
        n = self.cap
        yield self._s(0, f"enqueue({v}) started.")
        full = self._full()
        yield self._s(1, f"Is (rear + 1) % size == front ?  ({self.rear} + 1) % {n} = "
                         f"{(self.rear + 1) % n}  vs front = {self.front}  ->  {full}", "cmp")
        if full:
            yield self._s(2, "OVERFLOW - every slot is occupied.", "err")
            yield self._s(7, "END")
            return None
        if self.front == -1:
            self.front = 0
            yield self._s(3, "front was -1 (first element) so front = 0", hl=[0])
        else:
            yield self._s(3, f"front is already {self.front}, unchanged")
        old = self.rear
        self.rear = (self.rear + 1) % n
        wrapped = " (wrapped around to the start!)" if self.rear == 0 and old == n - 1 else ""
        yield self._s(4, f"rear = (rear + 1) % size  ->  rear = {self.rear}{wrapped}", hl=[self.rear])
        self.cells[self.rear] = (v, None)
        yield self._s(5, f"queue[{self.rear}] = {v}", event=("write", self.rear), hl=[self.rear])
        yield self._s(6, f"Success - {v} inserted at REAR.", "ok")
        yield self._s(7, "END")
        return v

    # -- remove from front (circular dequeue / deque deleteFront) --
    def dequeue(self):
        n = self.cap
        yield self._s(0, "dequeue() started.")
        empty = self._empty()
        yield self._s(1, f"Is front == -1 ?  front = {self.front}  ->  {empty}", "cmp")
        if empty:
            yield self._s(2, "UNDERFLOW - the queue is empty.", "err")
            yield self._s(7, "END")
            return None
        i = self.front
        v = self.cells[i][0]
        yield self._s(3, f"value = queue[{i}] = {v}", hl=[i])
        self.cells[i] = None
        if self.front == self.rear:
            self.front = self.rear = -1
            yield self._s(4, "front == rear: that was the last element, so front = rear = -1.",
                          event=("remove", i, v))
            yield self._s(5, "(else-branch skipped)")
        else:
            yield self._s(4, "front != rear: more elements remain.", event=("remove", i, v))
            self.front = (self.front + 1) % n
            wrapped = " (wrapped!)" if self.front == 0 else ""
            yield self._s(5, f"front = (front + 1) % size  ->  front = {self.front}{wrapped}")
        yield self._s(6, f"Success - removed {v} from FRONT.", "ok")
        yield self._s(7, "END")
        return v

    def peek(self):
        yield self._s(0, "peek() started.")
        if self._empty():
            yield self._s(1, "Queue is empty - nothing to peek.", "err")
            yield self._s(3, "END")
            return None
        v = self.cells[self.front][0]
        yield self._s(2, f"Front element is {v} (queue[{self.front}]).", "ok", hl=[self.front])
        yield self._s(3, "END")
        return v

    def display(self):
        n = self.cap
        yield self._s(0, "display() started.")
        if self._empty():
            yield self._s(1, "front == -1 -> true", "cmp")
            yield self._s(2, "Queue is empty", "err")
            yield self._s(8, "END")
            return []
        yield self._s(1, "Queue is not empty.", "cmp")
        i, out = self.front, []
        yield self._s(3, f"i = front = {i}", hl=[i])
        while True:
            yield self._s(4, "loop", hl=[i])
            out.append(self.cells[i][0])
            yield self._s(5, f"print queue[{i}] = {self.cells[i][0]}     (printed so far: {out})", hl=[i])
            at_end = i == self.rear
            yield self._s(6, f"Is i == rear ?  {i} == {self.rear}  ->  {at_end}", "cmp", hl=[i])
            if at_end:
                break
            i = (i + 1) % n
            yield self._s(7, f"i = (i + 1) % size  ->  i = {i}", hl=[i])
        yield self._s(8, f"Queue (front -> rear): {out}", "ok")
        return out


_RING_ENQ = ["START", "if (rear + 1) % size == front:", '    print "Overflow"; EXIT',
             "if front == -1: front = 0", "rear = (rear + 1) % size",
             "queue[rear] = value", "return success", "END"]
_RING_DEQ = ["START", "if front == -1:", '    print "Underflow"; EXIT', "value = queue[front]",
             "if front == rear: front = rear = -1", "else: front = (front + 1) % size",
             "return value", "END"]
_RING_PEEK = ["START", 'if front == -1: return "Queue is empty"', "return queue[front]", "END"]
_RING_DISP = ["START", "if front == -1:", '    print "Queue is empty"; EXIT', "i = front", "loop:",
              "    print queue[i]", "    if i == rear: break", "    i = (i + 1) % size", "END"]


class CircularQueue(RingQueue):
    TITLE = "Circular Queue"
    PSEUDO = {"enqueue": _RING_ENQ, "dequeue": _RING_DEQ, "peek": _RING_PEEK,
              "display": _RING_DISP,
              "is_empty": ["return front == -1"],
              "is_full": ["return (rear + 1) % size == front"]}


# ======================================================================
# 3. Double-ended queue
# ======================================================================
class Deque(RingQueue):
    TITLE = "Deque (Double-Ended Queue)"
    PSEUDO = {
        "insert_rear": _RING_ENQ,
        "delete_front": _RING_DEQ,
        "peek_front": _RING_PEEK,
        "display": _RING_DISP,
        "insert_front": ["START", "if (rear + 1) % size == front:", '    print "Overflow"; EXIT',
                         "if front == -1: front = rear = 0",
                         "else: front = (front - 1 + size) % size",
                         "queue[front] = value", "return success", "END"],
        "delete_rear": ["START", "if front == -1:", '    print "Underflow"; EXIT', "value = queue[rear]",
                        "if front == rear: front = rear = -1",
                        "else: rear = (rear - 1 + size) % size", "return value", "END"],
        "peek_rear": ["START", 'if front == -1: return "Queue is empty"', "return queue[rear]", "END"],
        "is_empty": ["return front == -1"],
        "is_full": ["return (rear + 1) % size == front"],
    }

    insert_rear = RingQueue.enqueue
    delete_front = RingQueue.dequeue
    peek_front = RingQueue.peek

    def insert_front(self, v):
        n = self.cap
        yield self._s(0, f"insertFront({v}) started.")
        full = self._full()
        yield self._s(1, f"Is (rear + 1) % size == front ?  ({self.rear} + 1) % {n} = "
                         f"{(self.rear + 1) % n}  vs front = {self.front}  ->  {full}", "cmp")
        if full:
            yield self._s(2, "OVERFLOW - every slot is occupied.", "err")
            yield self._s(7, "END")
            return None
        if self.front == -1:
            self.front = self.rear = 0
            yield self._s(3, "Deque was empty: front = rear = 0", hl=[0])
            yield self._s(4, "(else-branch skipped)")
        else:
            yield self._s(3, "Deque not empty: use the else-branch.")
            self.front = (self.front - 1 + n) % n
            wrapped = " (wrapped backwards to the end!)" if self.front == n - 1 else ""
            yield self._s(4, f"front = (front - 1 + size) % size  ->  front = {self.front}{wrapped}",
                          hl=[self.front])
        self.cells[self.front] = (v, None)
        yield self._s(5, f"queue[{self.front}] = {v}", event=("write", self.front), hl=[self.front])
        yield self._s(6, f"Success - {v} inserted at FRONT.", "ok")
        yield self._s(7, "END")
        return v

    def delete_rear(self):
        n = self.cap
        yield self._s(0, "deleteRear() started.")
        empty = self._empty()
        yield self._s(1, f"Is front == -1 ?  front = {self.front}  ->  {empty}", "cmp")
        if empty:
            yield self._s(2, "UNDERFLOW - the deque is empty.", "err")
            yield self._s(7, "END")
            return None
        i = self.rear
        v = self.cells[i][0]
        yield self._s(3, f"value = queue[{i}] = {v}", hl=[i])
        self.cells[i] = None
        if self.front == self.rear:
            self.front = self.rear = -1
            yield self._s(4, "front == rear: last element removed, front = rear = -1.",
                          event=("remove", i, v))
            yield self._s(5, "(else-branch skipped)")
        else:
            yield self._s(4, "front != rear: more elements remain.", event=("remove", i, v))
            self.rear = (self.rear - 1 + n) % n
            yield self._s(5, f"rear = (rear - 1 + size) % size  ->  rear = {self.rear}")
        yield self._s(6, f"Success - removed {v} from REAR.", "ok")
        yield self._s(7, "END")
        return v

    def peek_rear(self):
        yield self._s(0, "peekRear() started.")
        if self._empty():
            yield self._s(1, "Deque is empty - nothing to peek.", "err")
            yield self._s(3, "END")
            return None
        v = self.cells[self.rear][0]
        yield self._s(2, f"Rear element is {v} (queue[{self.rear}]).", "ok", hl=[self.rear])
        yield self._s(3, "END")
        return v


# ======================================================================
# 4. Priority queue (sorted array: lowest number = highest priority)
# ======================================================================
class PriorityQueue(BaseQueue):
    TITLE = "Priority Queue"
    PSEUDO = {
        "enqueue": ["START", "if size == capacity:", '    print "Overflow"; EXIT', "i = size - 1",
                    "while i >= 0 AND queue[i].priority > p:",
                    "    queue[i + 1] = queue[i]; i = i - 1      # shift right",
                    "queue[i + 1] = (value, p)", "size = size + 1", "return success", "END"],
        "dequeue": ["START", "if size == 0:", '    print "Underflow"; EXIT',
                    "item = queue[0]          # highest priority",
                    "for i from 1 to size - 1: queue[i - 1] = queue[i]   # shift left",
                    "size = size - 1", "return item", "END"],
        "peek": ["START", 'if size == 0: return "Queue is empty"', "return queue[0]", "END"],
        "display": ["START", "if size == 0:", '    print "Queue is empty"; EXIT',
                    "for i from 0 to size - 1:", "    print queue[i]", "END"],
        "is_empty": ["return size == 0"],
        "is_full": ["return size == capacity"],
    }

    def reset(self):
        self.cells = [None] * self.cap
        self._n = 0

    @property
    def front(self):
        return 0 if self._n else -1

    @property
    def rear(self):
        return self._n - 1

    def live(self):
        return set(range(self._n))

    def _empty(self):
        return self._n == 0

    def _full(self):
        return self._n == self.cap

    def enqueue(self, v, p):
        yield self._s(0, f"enqueue({v}, priority={p}) started.")
        full = self._full()
        yield self._s(1, f"Is size == capacity ?  {self._n} == {self.cap}  ->  {full}", "cmp")
        if full:
            yield self._s(2, "OVERFLOW - the queue is full.", "err")
            yield self._s(9, "END")
            return None
        i = self._n - 1
        yield self._s(3, f"i = size - 1 = {i}", hl=[i] if i >= 0 else [])
        while True:
            if i < 0:
                yield self._s(4, "i < 0: we reached the front, stop shifting.", "cmp")
                break
            ip = self.cells[i][1]
            go = ip > p
            yield self._s(4, f"queue[{i}].priority {ip} > {p} ?  {go}"
                             + ("  -> shift it right." if go else "  -> found the spot."),
                          "cmp", hl=[i], event=("compare", i))
            if not go:
                break
            self.cells[i + 1], self.cells[i] = self.cells[i], None
            yield self._s(5, f"queue[{i + 1}] = queue[{i}] ; i = {i - 1}",
                          event=("shift", i, i + 1), hl=[i + 1])
            i -= 1
        self.cells[i + 1] = (v, p)
        yield self._s(6, f"queue[{i + 1}] = ({v}, p={p})", event=("write", i + 1), hl=[i + 1])
        self._n += 1
        yield self._s(7, f"size = {self._n}", hl=[i + 1])
        yield self._s(8, f"Success - {v} (priority {p}) inserted in sorted position {i + 1}.", "ok")
        yield self._s(9, "END")
        return v

    def dequeue(self):
        yield self._s(0, "dequeue() started.")
        empty = self._empty()
        yield self._s(1, f"Is size == 0 ?  {self._n} == 0  ->  {empty}", "cmp")
        if empty:
            yield self._s(2, "UNDERFLOW - the queue is empty.", "err")
            yield self._s(7, "END")
            return None
        item = self.cells[0]
        self.cells[0] = None
        yield self._s(3, f"item = queue[0] = {item[0]} (priority {item[1]}) - the most urgent element.",
                      event=("remove", 0, item[0]), hl=[0])
        for i in range(1, self._n):
            self.cells[i - 1], self.cells[i] = self.cells[i], None
            yield self._s(4, f"queue[{i - 1}] = queue[{i}]   (shift left)", event=("shift", i, i - 1),
                          hl=[i - 1])
        self._n -= 1
        yield self._s(5, f"size = {self._n}")
        yield self._s(6, f"Success - removed {item[0]} (priority {item[1]}).", "ok")
        yield self._s(7, "END")
        return item[0]

    def peek(self):
        yield self._s(0, "peek() started.")
        if self._empty():
            yield self._s(1, "Queue is empty - nothing to peek.", "err")
            yield self._s(3, "END")
            return None
        v, p = self.cells[0]
        yield self._s(2, f"Highest priority element is {v} (priority {p}).", "ok", hl=[0])
        yield self._s(3, "END")
        return v

    def display(self):
        yield self._s(0, "display() started.")
        if self._empty():
            yield self._s(1, "size == 0 -> true", "cmp")
            yield self._s(2, "Queue is empty", "err")
            yield self._s(5, "END")
            return []
        yield self._s(1, "Queue is not empty.", "cmp")
        out = []
        for i in range(self._n):
            yield self._s(3, f"i = {i}", hl=[i])
            out.append(f"{self.cells[i][0]}(p{self.cells[i][1]})")
            yield self._s(4, f"print queue[{i}] = {out[-1]}", hl=[i])
        yield self._s(5, f"Queue (highest priority first): {out}", "ok")
        return out
