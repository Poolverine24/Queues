#!/usr/bin/env python3
"""
Queue Simulator - Simple (linear array) Queue.     Run:  python3 simple_queue.py

Values physically travel: they enter through the IN gate at the REAR and leave
through the OUT gate at the FRONT. While each operation animates, the matching
line of the algorithm (from the course slides) lights up automatically.
"""
import math
import random
import sys
import tkinter as tk

BG, PANEL, LINE = "#0f1226", "#181c38", "#2c3366"
TEXT, MUTED, DIM = "#eef0ff", "#8d95c7", "#4b5385"
CYAN, PINK, GREEN, RED, AMBER, VIOLET = "#22d3ee", "#f472b6", "#34d399", "#f87171", "#fbbf24", "#8b6cff"
CARD_COLORS = ["#8b6cff", "#3b82f6", "#06b6d4", "#10b981", "#f59e0b", "#ec4899", "#ef4444", "#a855f7"]
FONT = "Helvetica Neue"
CAP = 6

ALGO = {
    "enqueue": ["START", "if rear == size - 1:", '    print "Overflow"; EXIT', "rear = rear + 1",
                "if front == -1: front = 0", "queue[rear] = value", "return success", "END"],
    "dequeue": ["START", "if front == -1 OR front > rear:", '    print "Underflow"; EXIT',
                "value = queue[front]", "front = front + 1",
                "if front > rear: front = rear = -1", "return value", "END"],
    "peek": ["START", 'if empty: print "Queue is empty"', "return queue[front]", "END"],
    "display": ["START", "if front == -1 OR front > rear:", '    print "Queue is empty"; EXIT',
                "for i from front to rear:", "    print queue[i]", "END"],
    "is_empty": ["START", "return front == -1 OR front > rear", "END"],
    "is_full": ["START", "return rear == size - 1", "END"],
}
LABELS = {"enqueue": "Enqueue", "dequeue": "Dequeue", "peek": "Peek", "display": "Display",
          "is_empty": "isEmpty", "is_full": "isFull"}


def mix(a, b, t):
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3))


def rrect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
           x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class Card:
    """A value drawn on screen. It glides toward (tx, ty) every frame."""

    def __init__(self, value, color, x, y):
        self.value, self.color = value, color
        self.x, self.y, self.tx, self.ty = x, y, x, y
        self.s, self.ts = 0.4, 1.0          # scale and target scale
        self.fade, self.tfade = 0.0, 0.0    # 0 = solid, 1 = invisible
        self.glow = 0.0

    def step(self):
        k = 0.16
        self.x += (self.tx - self.x) * k
        self.y += (self.ty - self.y) * k
        self.s += (self.ts - self.s) * k
        self.fade += (self.tfade - self.fade) * 0.12
        self.glow *= 0.93


class Btn(tk.Label):
    def __init__(self, master, text, cmd, bg=PANEL, fg=TEXT, size=13, padx=14, pady=8):
        super().__init__(master, text=text, bg=bg, fg=fg, font=(FONT, size, "bold"), padx=padx, pady=pady,
                         cursor="hand2", highlightthickness=1, highlightbackground=LINE)
        self.base, self.cmd = bg, cmd
        self.bind("<Enter>", lambda e: self.config(bg=mix(self.base, "#ffffff", .15)))
        self.bind("<Leave>", lambda e: self.config(bg=self.base))
        self.bind("<ButtonRelease-1>", lambda e: self.cmd())

    def set_bg(self, bg):
        self.base = bg
        self.config(bg=bg)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Queue Simulator")
        self.geometry("1240x760")
        self.minsize(1100, 700)
        self.configure(bg=BG)

        # queue state, exactly as on the slides
        self.arr = [None] * CAP
        self.front = self.rear = -1
        self.cards = {}             # slot index -> Card
        self.leaving = []           # cards on their way out
        self.color_i = 0

        # animation state
        self.fx = self.rx = None    # drawn pointer positions (glide toward real ones)
        self.shake = 0.0
        self.badge = None           # (text, color, life)
        self.timeline, self.busy = [], False
        self.speed = 1.0
        self.last_in, self.code_op = "", "enqueue"

        self.build()
        self.after(50, self.frame)
        self.status("Type a value and press Enqueue (or hit Enter).", TEXT)

    # ================================================================ layout
    def build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=24, pady=(18, 6))
        tk.Label(top, text="Queue", bg=BG, fg=TEXT, font=(FONT, 28, "bold")).pack(side="left")
        tk.Label(top, text="  First In, First Out  -  enter at the REAR, leave from the FRONT",
                 bg=BG, fg=MUTED, font=(FONT, 14)).pack(side="left", pady=(10, 0))

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew")
        stats = tk.Frame(left, bg=BG)
        stats.pack(fill="x", pady=(0, 10))
        self.stat = {}
        for key, title, col in (("size", "SIZE", TEXT), ("front", "FRONT", CYAN), ("rear", "REAR", PINK),
                                ("cap", "CAPACITY", TEXT)):
            f = tk.Frame(stats, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            f.pack(side="left", padx=(0, 10))
            tk.Label(f, text=title, bg=PANEL, fg=MUTED, font=(FONT, 10, "bold")).pack(padx=18, pady=(8, 0))
            self.stat[key] = tk.Label(f, text="", bg=PANEL, fg=col, font=(FONT, 22, "bold"))
            self.stat[key].pack(padx=18, pady=(0, 6))

        self.canvas = tk.Canvas(left, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        self.canvas.pack(fill="both", expand=True)

        self.msg = tk.Label(left, text="", bg=BG, fg=TEXT, font=(FONT, 16, "bold"), anchor="w", justify="left")
        self.msg.pack(fill="x", pady=(10, 0))

        ctl = tk.Frame(left, bg=BG)
        ctl.pack(fill="x", pady=(10, 18))
        self.entry = tk.Entry(ctl, width=5, font=("Menlo", 18, "bold"), bg=PANEL, fg=TEXT, justify="center",
                              insertbackground=TEXT, relief="flat", highlightthickness=2,
                              highlightbackground=LINE, highlightcolor=VIOLET)
        self.entry.insert(0, "10")
        self.entry.pack(side="left", ipady=6, padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self.run("enqueue"))
        Btn(ctl, "Enqueue", lambda: self.run("enqueue"), bg=VIOLET).pack(side="left", padx=3)
        for op in ("dequeue", "peek", "display", "is_empty", "is_full"):
            Btn(ctl, LABELS[op], lambda o=op: self.run(o)).pack(side="left", padx=3)
        Btn(ctl, "Reset", self.reset, fg=MUTED).pack(side="right", padx=3)
        Btn(ctl, "Random", self.random_fill, fg=MUTED).pack(side="right", padx=3)

        right = tk.Frame(body, bg=BG, width=360)
        right.grid(row=0, column=1, sticky="ns", padx=(18, 0))
        right.pack_propagate(False)

        algo = tk.Frame(right, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        algo.pack(fill="x")
        self.algo_title = tk.Label(algo, text="", bg=PANEL, fg=MUTED, font=(FONT, 11, "bold"), anchor="w")
        self.algo_title.pack(fill="x", padx=14, pady=(12, 4))
        self.code = tk.Text(algo, bg=PANEL, fg=MUTED, font=("Menlo", 12), relief="flat", height=8,
                            highlightthickness=0, padx=10, cursor="arrow", wrap="none")
        self.code.pack(fill="x", padx=4, pady=(0, 12))
        self.code.tag_configure("now", background="#3b3f98", foreground="#ffffff")

        speed = tk.Frame(right, bg=BG)
        speed.pack(fill="x", pady=10)
        tk.Label(speed, text="SPEED", bg=BG, fg=MUTED, font=(FONT, 10, "bold")).pack(side="left", padx=(2, 10))
        self.speed_btns = {}
        for name, val in (("Slow", 1.8), ("Normal", 1.0), ("Fast", 0.45)):
            b = Btn(speed, name, lambda v=val: self.set_speed(v), size=11, padx=10, pady=4)
            b.pack(side="left", padx=2)
            self.speed_btns[val] = b
        self.set_speed(1.0)

        out = tk.Frame(right, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        out.pack(fill="x")
        tk.Label(out, text="OUTPUT", bg=PANEL, fg=MUTED, font=(FONT, 11, "bold"), anchor="w").pack(fill="x", padx=14, pady=(12, 0))
        self.output = tk.Label(out, text="-", bg=PANEL, fg=GREEN, font=("Menlo", 18, "bold"), anchor="w",
                               wraplength=320, justify="left")
        self.output.pack(fill="x", padx=14, pady=(2, 12))

        hist = tk.Frame(right, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        hist.pack(fill="both", expand=True, pady=(10, 18))
        tk.Label(hist, text="HISTORY", bg=PANEL, fg=MUTED, font=(FONT, 11, "bold"), anchor="w").pack(fill="x", padx=14, pady=(12, 2))
        self.hist = tk.Text(hist, bg=PANEL, fg=TEXT, font=("Menlo", 12), relief="flat", highlightthickness=0,
                            padx=12, cursor="arrow", wrap="word", spacing1=2)
        self.hist.pack(fill="both", expand=True, pady=(0, 8))
        for k, col in (("ok", GREEN), ("err", RED), ("info", MUTED)):
            self.hist.tag_configure(k, foreground=col)
        self.show_algo("enqueue")
        self.refresh_stats()

    # ================================================================ helpers
    def set_speed(self, v):
        self.speed = v
        for val, b in self.speed_btns.items():
            b.set_bg(VIOLET if val == v else PANEL)

    def status(self, text, color):
        self.msg.config(text=text, fg=color)

    def show_algo(self, op, line=None):
        self.algo_title.config(text=f"ALGORITHM  -  {LABELS[op].upper()}")
        self.code.config(state="normal")
        self.code.delete("1.0", "end")
        for i, l in enumerate(ALGO[op]):
            self.code.insert("end", f"{i + 1:>2}  {l}\n")
        if line is not None:
            self.code.tag_add("now", f"{line + 1}.0", f"{line + 1}.end+1c")
        self.code.config(state="disabled", height=len(ALGO[op]))

    def history(self, text, kind):
        self.hist.config(state="normal")
        self.hist.insert("1.0", text + "\n", kind)
        self.hist.config(state="disabled")

    def refresh_stats(self):
        size = 0 if self.front == -1 or self.front > self.rear else self.rear - self.front + 1
        self.stat["size"].config(text=str(size))
        self.stat["front"].config(text=str(self.front))
        self.stat["rear"].config(text=str(self.rear))
        self.stat["cap"].config(text=str(CAP))

    def empty(self):
        return self.front == -1 or self.front > self.rear

    def full(self):
        return self.rear == CAP - 1

    # geometry (recomputed every frame so resizing works)
    def geo(self):
        W, H = self.canvas.winfo_width(), self.canvas.winfo_height()
        gate = 90
        sw = min(110, (W - 2 * gate - 40) / CAP)
        x0 = (W - CAP * sw) / 2
        return W, H, x0, sw, H * 0.5

    def slot_center(self, i):
        _, _, x0, sw, y = self.geo()
        return x0 + (i + 0.5) * sw, y

    # ================================================================ timeline
    def run(self, op):
        if self.busy:
            self.status("Wait for the current operation to finish...", AMBER)
            return
        value = None
        if op == "enqueue":
            value = self.entry.get().strip()
            if not value or len(value) > 4:
                self.status("Type a value (1 to 4 characters) in the box first.", RED)
                self.entry.focus_set()
                return
        self.show_algo(op)
        self.output.config(text="-", fg=GREEN)
        self.timeline = getattr(self, "op_" + op)(*([value] if value else []))
        self.busy = True
        self.next_beat()

    def next_beat(self):
        if not self.timeline:
            self.busy = False
            self.show_algo(self.code_op, None)
            self.refresh_stats()
            if self.code_op == "enqueue" and self.last_in.isdigit():   # suggest the next value
                self.entry.delete(0, "end")
                self.entry.insert(0, str(int(self.last_in) + 10))
            return
        op, line, text, color, fn, weight = self.timeline.pop(0)
        self.code_op = op
        self.show_algo(op, line)
        if text:
            self.status(text, color)
        if fn:
            fn()
        self.refresh_stats()
        self.after(int(650 * weight * self.speed), self.next_beat)

    # Each op returns a list of beats: (op, line, message, colour, action, duration-weight)
    def op_enqueue(self, v):
        self.last_in = v
        E = "enqueue"
        beats = [(E, 0, f"Enqueue {v}: start.", TEXT, None, .6)]
        if self.full():
            beats += [(E, 1, f"Is rear == size - 1?   {self.rear} == {CAP - 1}  ->  YES, the queue is full.", AMBER, None, 1.2),
                      (E, 2, f"OVERFLOW! No room for {v}.", RED, lambda: self.alarm("OVERFLOW", v), 1.6),
                      (E, 7, "", None, None, .4)]
            return beats
        def move_rear():
            self.rear += 1
        def set_front():
            if self.front == -1:
                self.front = 0
        def place():
            self.arr[self.rear] = v
            c = Card(v, CARD_COLORS[self.color_i % len(CARD_COLORS)], *self.in_gate())
            self.color_i += 1
            c.tx, c.ty = self.slot_center(self.rear)
            self.cards[self.rear] = c
        first = self.front == -1
        beats += [
            (E, 1, f"Is rear == size - 1?   {self.rear} == {CAP - 1}  ->  no, there is space.", AMBER, None, 1.1),
            (E, 3, f"Move REAR one step right:  rear = {self.rear + 1}", PINK, move_rear, 1.0),
            (E, 4, "First element, so FRONT = 0 as well." if first else "FRONT does not change.",
             CYAN, set_front, .9 if first else .6),
            (E, 5, f"{v} enters through the IN gate into slot {self.rear + 1}.", TEXT, place, 1.4),
            (E, 6, f"Done - {v} added at the rear.", GREEN, lambda: self.done(f"Enqueued {v}", "ok"), .8),
            (E, 7, "", None, None, .3)]
        return beats

    def op_dequeue(self):
        D = "dequeue"
        beats = [(D, 0, "Dequeue: start.", TEXT, None, .6)]
        if self.empty():
            beats += [(D, 1, f"Is front == -1 OR front > rear?   front = {self.front}  ->  YES, empty.", AMBER, None, 1.2),
                      (D, 2, "UNDERFLOW! There is nothing to remove.", RED, lambda: self.alarm("UNDERFLOW"), 1.6),
                      (D, 7, "", None, None, .4)]
            return beats
        v = self.arr[self.front]
        def take():
            c = self.cards.get(self.front)
            if c:
                c.glow = 1.0
                c.ty -= 20
        def leave():
            c = self.cards.pop(self.front, None)
            self.arr[self.front] = None
            if c:
                c.tx, c.ty = self.out_gate()
                c.ts, c.tfade = .5, 1.0
                self.leaving.append(c)
            self.front += 1
            self.output.config(text=str(v))
        def maybe_reset():
            if self.front > self.rear:
                self.front = self.rear = -1
        last = self.front == self.rear
        beats += [
            (D, 1, f"Is front == -1 OR front > rear?   ({self.front}, {self.rear})  ->  no, not empty.", AMBER, None, 1.1),
            (D, 3, f"Take the value at the FRONT:  queue[{self.front}] = {v}", CYAN, take, 1.0),
            (D, 4, f"{v} leaves through the OUT gate, FRONT moves right.", TEXT, leave, 1.4),
            (D, 5, "Queue is now empty -> reset front = rear = -1." if last else "Still elements left, no reset.",
             MUTED, maybe_reset, .9 if last else .5),
            (D, 6, f"Done - {v} removed from the front.", GREEN, lambda: self.done(f"Dequeued {v}", "ok"), .8),
            (D, 7, "", None, None, .3)]
        return beats

    def op_peek(self):
        P = "peek"
        if self.empty():
            return [(P, 0, "Peek: start.", TEXT, None, .5),
                    (P, 1, "Queue is empty - nothing to see.", RED, lambda: self.alarm("EMPTY"), 1.4),
                    (P, 3, "", None, None, .3)]
        v = self.arr[self.front]
        def look():
            self.cards[self.front].glow = 1.0
            self.output.config(text=str(v))
        return [(P, 0, "Peek: start.", TEXT, None, .5),
                (P, 2, f"The FRONT element is {v}. It is NOT removed.", CYAN, look, 1.5),
                (P, 3, "", None, lambda: self.done(f"Peek -> {v}", "ok"), .3)]

    def op_display(self):
        S = "display"
        beats = [(S, 0, "Display: start.", TEXT, None, .5)]
        if self.empty():
            return beats + [(S, 1, "front == -1 -> the queue is empty.", AMBER, None, 1.0),
                            (S, 2, "Queue is empty.", RED, lambda: self.alarm("EMPTY"), 1.3),
                            (S, 5, "", None, None, .3)]
        beats.append((S, 1, "Not empty, so print from FRONT to REAR.", AMBER, None, .9))
        printed = []
        for i in range(self.front, self.rear + 1):
            def show(i=i):
                self.cards[i].glow = 1.0
                printed.append(str(self.arr[i]))
                self.output.config(text="  ".join(printed))
            beats.append((S, 3, f"i = {i}", MUTED, None, .45))
            beats.append((S, 4, f"print queue[{i}] = {self.arr[i]}", TEXT, show, .9))
        beats.append((S, 5, "Done - all elements printed front to rear.", GREEN,
                      lambda: self.done("Display -> " + " ".join(printed), "ok"), .5))
        return beats

    def op_is_empty(self):
        ans = self.empty()
        return [("is_empty", 0, "isEmpty: start.", TEXT, None, .4),
                ("is_empty", 1, f"front == -1 OR front > rear?   front = {self.front}, rear = {self.rear}  ->  {ans}",
                 GREEN if ans else RED, lambda: self.answer(ans), 1.5),
                ("is_empty", 2, "", None, lambda: self.done(f"isEmpty -> {ans}", "ok"), .3)]

    def op_is_full(self):
        ans = self.full()
        return [("is_full", 0, "isFull: start.", TEXT, None, .4),
                ("is_full", 1, f"rear == size - 1?   {self.rear} == {CAP - 1}  ->  {ans}",
                 GREEN if ans else RED, lambda: self.answer(ans), 1.5),
                ("is_full", 2, "", None, lambda: self.done(f"isFull -> {ans}", "ok"), .3)]

    # ---------------------------------------------------------------- effects
    def in_gate(self):
        W, H, x0, sw, y = self.geo()
        return x0 + CAP * sw + 60, y

    def out_gate(self):
        W, H, x0, sw, y = self.geo()
        return x0 - 70, y

    def alarm(self, word, v=None):
        self.shake = 1.0
        self.badge = [word, RED, 1.0]
        self.output.config(text=word, fg=RED)
        self.history(f"{word}" + (f" ({v})" if v else ""), "err")

    def answer(self, ans):
        self.badge = [str(ans).upper(), GREEN if ans else RED, 1.0]
        self.output.config(text=str(ans), fg=GREEN if ans else RED)

    def done(self, text, kind):
        self.history(text, kind)

    def reset(self):
        if self.busy:
            return
        self.arr = [None] * CAP
        self.front = self.rear = -1
        for c in self.cards.values():
            c.tfade, c.ts = 1.0, .3
            self.leaving.append(c)
        self.cards = {}
        self.output.config(text="-", fg=GREEN)
        self.refresh_stats()
        self.status("Queue reset. Everything is empty again.", MUTED)
        self.history("Reset", "info")

    def random_fill(self):
        if self.busy:
            return
        self.reset()
        for k in range(random.randint(2, CAP - 1)):
            v = str(random.randint(1, 99))
            self.rear += 1
            self.front = 0
            self.arr[self.rear] = v
            c = Card(v, CARD_COLORS[self.color_i % len(CARD_COLORS)], *self.in_gate())
            self.color_i += 1
            c.tx, c.ty = self.slot_center(self.rear)
            c.x += k * 50
            self.cards[self.rear] = c
        self.refresh_stats()
        self.status("Filled with random values.", MUTED)
        self.history("Random fill", "info")

    # ================================================================ drawing (60 fps)
    def frame(self):
        c = self.canvas
        c.delete("all")
        W, H, x0, sw, y = self.geo()
        if W > 200 and H > 150:
            self.shake *= 0.9
            dx = math.sin(self.shake * 40) * 14 * self.shake if self.shake > .02 else 0
            self.draw_lane(c, W, H, x0 + dx, sw, y)
            for i, card in list(self.cards.items()):
                card.tx, card.ty = card.tx if card.tfade else (x0 + (i + .5) * sw), card.ty
                card.step()
                self.draw_card(c, card, sw, dx)
            for card in self.leaving[:]:
                card.step()
                if card.fade > .95:
                    self.leaving.remove(card)
                else:
                    self.draw_card(c, card, sw, 0)
            self.draw_pointers(c, x0 + dx, sw, y)
            self.draw_badge(c, W, H)
        self.after(16, self.frame)

    def draw_lane(self, c, W, H, x0, sw, y):
        h = min(90, sw * .9)
        xe = x0 + CAP * sw
        rrect(c, x0 - 14, y - h / 2 - 14, xe + 14, y + h / 2 + 14, 22, fill="#121633", outline=LINE, width=2)
        for i in range(CAP):
            xa, xb = x0 + i * sw + 6, x0 + (i + 1) * sw - 6
            used = i < self.front and self.front != -1 and self.full()
            rrect(c, xa, y - h / 2, xb, y + h / 2, 12, fill=PANEL, outline=AMBER if used else LINE,
                  width=2, dash=(5, 4))
            c.create_text((xa + xb) / 2, y + h / 2 + 34, text=f"[{i}]", fill=MUTED, font=("Menlo", 12))
        # gates
        ox, ix = x0 - 70, xe + 60
        for x, word, col, arrow in ((ox, "OUT", CYAN, "<"), (ix, "IN", PINK, "<")):
            rrect(c, x - 34, y - 22, x + 34, y + 22, 12, fill=mix(col, PANEL, .82), outline=col, width=2)
            c.create_text(x, y, text=word, fill=col, font=(FONT, 14, "bold"))
        c.create_text(ix, y + 44, text="new values", fill=MUTED, font=(FONT, 10))
        c.create_text(ox, y + 44, text="leave here", fill=MUTED, font=(FONT, 10))
        if self.front > 0 and self.full():
            c.create_text((x0 + x0 + self.front * sw) / 2, y - h / 2 - 32, text="free but cannot be reused",
                          fill=AMBER, font=(FONT, 11, "bold"))
        if self.empty():
            c.create_text(W / 2, y - h / 2 - 34, text="(queue is empty)", fill=DIM, font=(FONT, 13, "bold"))

    def draw_card(self, c, card, sw, dx):
        w = min(90, sw * .78) * card.s
        x, y = card.x + dx, card.y
        col = mix(card.color, PANEL, card.fade)
        if card.glow > .05:
            g = 10 * card.glow
            rrect(c, x - w / 2 - g, y - w / 2 - g, x + w / 2 + g, y + w / 2 + g, 18,
                  fill="", outline=mix(AMBER, PANEL, 1 - card.glow), width=4)
        rrect(c, x - w / 2, y - w / 2, x + w / 2, y + w / 2, 14, fill=col, outline=mix("#ffffff", col, .7), width=1)
        size = max(9, int((24 if len(card.value) <= 2 else 18) * card.s))
        c.create_text(x, y, text=card.value, fill=mix("#ffffff", PANEL, card.fade), font=(FONT, size, "bold"))

    def draw_pointers(self, c, x0, sw, y):
        h = min(90, sw * .9)
        parked = x0 - 70
        tf = parked if self.front == -1 else x0 + (self.front + .5) * sw
        tr = parked if self.rear == -1 else x0 + (self.rear + .5) * sw
        self.fx = tf if self.fx is None else self.fx + (tf - self.fx) * .15
        self.rx = tr if self.rx is None else self.rx + (tr - self.rx) * .15
        ty = y - h / 2 - 22              # REAR above
        c.create_polygon(self.rx - 11, ty - 16, self.rx + 11, ty - 16, self.rx, ty, fill=PINK, outline="")
        c.create_text(self.rx, ty - 30, text=f"REAR = {self.rear}", fill=PINK, font=(FONT, 13, "bold"))
        by = y + h / 2 + 52              # FRONT below
        c.create_polygon(self.fx - 11, by + 16, self.fx + 11, by + 16, self.fx, by, fill=CYAN, outline="")
        c.create_text(self.fx, by + 30, text=f"FRONT = {self.front}", fill=CYAN, font=(FONT, 13, "bold"))

    def draw_badge(self, c, W, H):
        if not self.badge:
            return
        text, col, life = self.badge
        pop = min(1.0, (1 - life) * 6)
        size = int(16 + 16 * pop)
        c.create_text(W / 2, 46, text=text, fill=mix(col, PANEL, max(0, 1 - life * 1.4)), font=(FONT, size, "bold"))
        self.badge[2] -= 0.008 / self.speed
        if self.badge[2] <= 0:
            self.badge = None


def selftest():
    app = App()
    app.set_speed(0.01)
    app.update()

    def drain():
        while app.busy:
            app.update()
    for op in ["dequeue", "peek", "display", "is_empty"] + ["enqueue"] * 7 + ["is_full", "display", "peek"] \
            + ["dequeue"] * 7 + ["is_empty"]:
        app.run(op)
        drain()
    assert app.front == app.rear == -1, (app.front, app.rear)
    app.random_fill()
    for _ in range(30):
        app.update()
    print("selftest OK")
    app.destroy()


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else App().mainloop()
