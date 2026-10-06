#!/usr/bin/env python3
"""
Queue Simulator - DAA prototype (Tkinter, standard library only).

Run:   python3 queue_simulator.py
Test:  python3 queue_simulator.py --selftest      (drives every operation headlessly)

Four tabs - Simple, Circular, Priority and Deque - each animate enqueue / dequeue /
peek / display step by step, highlight the matching line of pseudocode, and explain
every step in plain English. The Simple Queue follows the course slides exactly.
"""
import math
import random
import sys
import tkinter as tk
from tkinter import ttk

from queue_logic import LinearQueue, CircularQueue, Deque, PriorityQueue

# ---------------------------------------------------------------- theme
BG, BG2 = "#0e1124", "#141833"
CARD, CARD2 = "#1a1f3d", "#222850"
BORDER = "#2f3766"
TEXT, MUTED, MUTED_D = "#e9ecff", "#8f98cc", "#4a5287"
ACCENT, ACCENT_D = "#8b6cff", "#2c2f6e"
CYAN, PINK, GREEN, GREEN_D = "#22d3ee", "#f472b6", "#34d399", "#0f5a45"
RED, AMBER = "#f87171", "#fbbf24"
KIND_COLOR = {"info": TEXT, "ok": GREEN, "err": RED, "cmp": AMBER}
PRI_COLOR = {1: RED, 2: AMBER, 3: GREEN, 4: CYAN}          # 5+ falls back to ACCENT

SANS = ("Helvetica Neue", 12)
SANS_B = ("Helvetica Neue", 12, "bold")
MONO = ("Menlo", 12)
MONO_S = ("Menlo", 11)


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3))


def ease(t):
    return t * t * (3 - 2 * t)


def rr(x1, y1, x2, y2, r):
    """Points for a rounded rectangle (use with smooth=True)."""
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


class Btn(tk.Label):
    """Flat label-button (native macOS buttons ignore background colours)."""

    def __init__(self, master, text, command, bg=CARD2, fg=TEXT, hover=None, font=SANS_B,
                 padx=12, pady=6):
        super().__init__(master, text=text, bg=bg, fg=fg, font=font, padx=padx, pady=pady,
                         cursor="hand2")
        self._bg, self._hover, self._cmd = bg, hover or mix(bg, "#ffffff", .14), command
        self.bind("<Enter>", lambda e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))
        self.bind("<ButtonRelease-1>", lambda e: self._cmd())


# ---------------------------------------------------------------- per-queue metadata
META = {
    LinearQueue: dict(
        views=("row",),
        ops=[("Enqueue", "enqueue", "v"), ("Dequeue", "dequeue", ""), ("Peek", "peek", ""),
             ("Display", "display", ""), ("isEmpty", "is_empty", ""), ("isFull", "is_full", "")],
        cplx={"enqueue": "O(1)", "dequeue": "O(1)", "peek": "O(1)", "display": "O(n)",
              "is_empty": "O(1)", "is_full": "O(1)"},
        theory=("A queue is a linear data structure that follows FIFO (First In, First Out): "
                "the first element inserted is the first one removed. Insertion happens at the "
                "REAR, deletion at the FRONT - like people waiting in line for a rail ticket.\n"
                "Weakness: after dequeues the freed slots in front of FRONT are never reused "
                "(unless the queue becomes completely empty and is reset). Try the demo!"),
        demo_cap=5, demo_note=("Demo: fill all 5 slots, dequeue 3, then enqueue 99. Slots 0-2 are free, "
                               "but REAR is already at the end -> Overflow. Circular Queue fixes this."),
    ),
    CircularQueue: dict(
        views=("ring", "row"),
        ops=[("Enqueue", "enqueue", "v"), ("Dequeue", "dequeue", ""), ("Peek", "peek", ""),
             ("Display", "display", ""), ("isEmpty", "is_empty", ""), ("isFull", "is_full", "")],
        cplx={"enqueue": "O(1)", "dequeue": "O(1)", "peek": "O(1)", "display": "O(n)",
              "is_empty": "O(1)", "is_full": "O(1)"},
        theory=("A circular queue joins the end of the array back to the start, so FRONT and REAR "
                "wrap around using modulo: rear = (rear + 1) % size. Freed slots are reused, so "
                "no space is wasted. Full when (rear + 1) % size == front; empty when front == -1."),
        demo_cap=5, demo_note=("Demo: fill 5 slots, dequeue 3, then enqueue 77. REAR wraps around to "
                               "index 0 and reuses a freed slot - the Simple Queue could not do this."),
    ),
    PriorityQueue: dict(
        views=("row",),
        ops=[("Enqueue", "enqueue", "vp"), ("Dequeue", "dequeue", ""), ("Peek", "peek", ""),
             ("Display", "display", ""), ("isEmpty", "is_empty", ""), ("isFull", "is_full", "")],
        cplx={"enqueue": "O(n)", "dequeue": "O(n)", "peek": "O(1)", "display": "O(n)",
              "is_empty": "O(1)", "is_full": "O(1)"},
        theory=("In a priority queue every element has a priority and the most urgent one leaves "
                "first (here: smaller number = higher priority; equal priorities stay FIFO). This "
                "array version keeps the list sorted: insert shifts larger priorities right - O(n); "
                "a binary heap would make both operations O(log n)."),
        demo_cap=6, demo_note=("Demo: queue holds x(p5), y(p1), z(p3). Enqueue w with priority 2 - it "
                               "is inserted in sorted position, shifting x and z to the right."),
    ),
    Deque: dict(
        views=("ring", "row"),
        ops=[("Insert Front", "insert_front", "v"), ("Insert Rear", "insert_rear", "v"),
             ("Delete Front", "delete_front", ""), ("Delete Rear", "delete_rear", ""),
             ("Peek Front", "peek_front", ""), ("Peek Rear", "peek_rear", ""),
             ("Display", "display", ""), ("isEmpty", "is_empty", ""), ("isFull", "is_full", "")],
        cplx={"insert_front": "O(1)", "insert_rear": "O(1)", "delete_front": "O(1)",
              "delete_rear": "O(1)", "peek_front": "O(1)", "peek_rear": "O(1)", "display": "O(n)",
              "is_empty": "O(1)", "is_full": "O(1)"},
        theory=("A double-ended queue (deque) allows insertion AND deletion at both ends, so it can "
                "behave as a queue, a stack, or both. Implemented on a circular array: FRONT moves "
                "backwards with (front - 1 + size) % size, REAR moves forwards with (rear + 1) % size."),
        demo_cap=5, demo_note=("Demo: deque holds 10, 20, 30 (front=0). Insert 5 at the FRONT - FRONT "
                               "wraps backwards to the last index."),
    ),
}
TAB_TITLES = [(LinearQueue, "  Simple Queue  "), (CircularQueue, "  Circular Queue  "),
              (PriorityQueue, "  Priority Queue  "), (Deque, "  Deque  ")]


# ---------------------------------------------------------------- one tab
class QueuePanel(tk.Frame):
    def __init__(self, master, cls):
        super().__init__(master, bg=BG)
        self.cls, self.meta = cls, META[cls]
        self.q = cls(6)
        self.steps, self.idx, self.logged = [], -1, -1
        self.pre = self.q.snapshot()
        self.prev_snap = self.cur_snap = self.pre
        self.cur_op = self.meta["ops"][0][1]
        self.playing, self.t, self._job, self._tween = False, 1.0, None, None
        self.note = None
        self.view = tk.StringVar(value=self.meta["views"][0])
        self.auto = tk.BooleanVar(value=True)
        self.speed = tk.DoubleVar(value=1.0)
        self.reset_opt = tk.BooleanVar(value=True)
        self.stat = {k: tk.StringVar(value="-") for k in ("size", "cap", "front", "rear", "free")}
        self.build()
        self.set_pseudo(self.cur_op)
        self.log("hdr", f"{cls.TITLE} created with capacity {self.q.cap}.")
        self.canvas.bind("<Configure>", lambda e: self.render())

    # ------------------------------------------------------------ layout
    def build(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.build_controls()
        self.build_center()
        self.build_right()

    def card(self, parent, title=None):
        f = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        if title:
            tk.Label(f, text=title.upper(), bg=CARD, fg=MUTED, font=("Helvetica Neue", 10, "bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(10, 4))
        return f

    def build_controls(self):
        left = tk.Frame(self, bg=BG, width=250)
        left.grid(row=0, column=0, sticky="ns", padx=(14, 7), pady=14)
        left.grid_propagate(False)

        c = self.card(left, "Setup")
        c.pack(fill="x")
        row = tk.Frame(c, bg=CARD); row.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(row, text="Capacity", bg=CARD, fg=TEXT, font=SANS).pack(side="left")
        self.cap_var = tk.StringVar(value="6")
        tk.Spinbox(row, from_=2, to=12, width=3, textvariable=self.cap_var, bg=CARD2, fg=TEXT,
                   insertbackground=TEXT, buttonbackground=CARD2, relief="flat", font=SANS,
                   highlightthickness=1, highlightbackground=BORDER).pack(side="left", padx=8)
        Btn(row, "Create", self.new_queue, bg=ACCENT_D).pack(side="right")
        if self.cls is LinearQueue:
            ttk.Checkbutton(c, text="Optional reset when empty\n(step 6 of dequeue)", variable=self.reset_opt,
                            style="Q.TCheckbutton").pack(anchor="w", padx=12, pady=(0, 10))
        elif len(self.meta["views"]) > 1:
            r = tk.Frame(c, bg=CARD); r.pack(fill="x", padx=12, pady=(0, 10))
            tk.Label(r, text="View", bg=CARD, fg=TEXT, font=SANS).pack(side="left")
            for v, label in (("ring", "Ring"), ("row", "Row")):
                ttk.Radiobutton(r, text=label, value=v, variable=self.view, style="Q.TRadiobutton",
                                command=self.render).pack(side="left", padx=6)

        c = self.card(left, "Input")
        c.pack(fill="x", pady=10)
        row = tk.Frame(c, bg=CARD); row.pack(fill="x", padx=12, pady=(0, 6))
        tk.Label(row, text="Value", bg=CARD, fg=TEXT, font=SANS, width=8, anchor="w").pack(side="left")
        self.val = tk.Entry(row, width=8, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat",
                            font=MONO, highlightthickness=1, highlightbackground=BORDER,
                            highlightcolor=ACCENT)
        self.val.insert(0, "42"); self.val.pack(side="left", fill="x", expand=True)
        self.pri = None
        if self.cls is PriorityQueue:
            row = tk.Frame(c, bg=CARD); row.pack(fill="x", padx=12, pady=(0, 6))
            tk.Label(row, text="Priority", bg=CARD, fg=TEXT, font=SANS, width=8, anchor="w").pack(side="left")
            self.pri = tk.Entry(row, width=8, bg=CARD2, fg=TEXT, insertbackground=TEXT, relief="flat",
                                font=MONO, highlightthickness=1, highlightbackground=BORDER,
                                highlightcolor=ACCENT)
            self.pri.insert(0, "2"); self.pri.pack(side="left", fill="x", expand=True)
            tk.Label(c, text="1 = most urgent", bg=CARD, fg=MUTED, font=("Helvetica Neue", 10)
                     ).pack(anchor="w", padx=12)
        tk.Frame(c, bg=CARD, height=6).pack()

        c = self.card(left, "Operations")
        c.pack(fill="x")
        self.opbtns = {}
        grid = tk.Frame(c, bg=CARD); grid.pack(fill="x", padx=10, pady=(0, 10))
        for i, (label, method, need) in enumerate(self.meta["ops"]):
            primary = need != "" or method.startswith("insert")
            b = Btn(grid, label, lambda m=method, n=need: self.exec(m, n),
                    bg=ACCENT if primary else CARD2, hover=mix(ACCENT, "#ffffff", .15) if primary else None)
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=3, pady=3)
            self.opbtns[method] = b
        grid.columnconfigure((0, 1), weight=1)
        self.val.bind("<Return>", lambda e: self.exec(self.meta["ops"][0][1], self.meta["ops"][0][2]))

        c = self.card(left, "Quick actions")
        c.pack(fill="x", pady=10)
        inner = tk.Frame(c, bg=CARD); inner.pack(fill="x", padx=10, pady=(0, 10))
        Btn(inner, "Demo", self.demo, bg=mix(GREEN_D, CARD, .2), fg=GREEN).pack(fill="x", pady=3)
        Btn(inner, "Random fill", self.random_fill).pack(fill="x", pady=3)
        Btn(inner, "Clear queue", self.clear).pack(fill="x", pady=3)

    def build_center(self):
        mid = tk.Frame(self, bg=BG)
        mid.grid(row=0, column=1, sticky="nsew", padx=7, pady=14)
        mid.rowconfigure(1, weight=1)
        mid.columnconfigure(0, weight=1)

        chips = tk.Frame(mid, bg=BG); chips.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.chip_labels = []
        for key, title, color in (("size", "SIZE", TEXT), ("cap", "CAPACITY", TEXT), ("front", "FRONT", CYAN),
                                  ("rear", "REAR", PINK), ("free", "FREE SLOTS", GREEN)):
            f = tk.Frame(chips, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            f.pack(side="left", padx=(0, 8))
            tk.Label(f, text=title, bg=CARD, fg=MUTED, font=("Helvetica Neue", 9, "bold")).pack(padx=14, pady=(6, 0))
            tk.Label(f, textvariable=self.stat[key], bg=CARD, fg=color,
                     font=("Helvetica Neue", 18, "bold")).pack(padx=14, pady=(0, 4))
        self.wasted_lbl = tk.Label(chips, text="", bg=BG, fg=AMBER, font=SANS_B)
        self.wasted_lbl.pack(side="left", padx=6)

        self.canvas = tk.Canvas(mid, bg=BG2, highlightthickness=1, highlightbackground=BORDER, height=380)
        self.canvas.grid(row=1, column=0, sticky="nsew")

        bar = tk.Frame(mid, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        bar.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        inner = tk.Frame(bar, bg=CARD); inner.pack(fill="x", padx=10, pady=8)
        for text, cmd in (("|<", lambda: self.goto(0)), ("<", lambda: self.goto(self.idx - 1))):
            Btn(inner, text, lambda c=cmd: (self.pause(), c())).pack(side="left", padx=2)
        self.play_btn = Btn(inner, "Play", self.toggle_play, bg=ACCENT, padx=16)
        self.play_btn.pack(side="left", padx=2)
        for text, cmd in ((">", lambda: self.goto(self.idx + 1)), (">|", lambda: self.goto(len(self.steps) - 1))):
            Btn(inner, text, lambda c=cmd: (self.pause(), c())).pack(side="left", padx=2)
        self.step_lbl = tk.Label(inner, text="No operation yet", bg=CARD, fg=MUTED, font=SANS, width=18)
        self.step_lbl.pack(side="left", padx=10)
        ttk.Checkbutton(inner, text="Auto-play", variable=self.auto, style="Q.TCheckbutton").pack(side="left", padx=6)
        tk.Label(inner, text="Speed", bg=CARD, fg=MUTED, font=SANS).pack(side="left", padx=(14, 4))
        ttk.Scale(inner, from_=0.25, to=3.0, variable=self.speed, length=130, style="Q.Horizontal.TScale"
                  ).pack(side="left")

        info = tk.Frame(mid, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        info.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        tk.Label(info, text=self.meta["theory"], bg=CARD, fg=TEXT, font=("Helvetica Neue", 11), justify="left",
                 anchor="w", wraplength=720).pack(fill="x", padx=12, pady=(8, 4))
        pills = tk.Frame(info, bg=CARD); pills.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(pills, text="TIME COMPLEXITY", bg=CARD, fg=MUTED, font=("Helvetica Neue", 9, "bold")
                 ).pack(side="left", padx=(2, 8))
        self.pills = {}
        for label, method, _ in self.meta["ops"]:
            if method in ("is_empty", "is_full"):
                continue
            p = tk.Label(pills, text=f"{label} {self.meta['cplx'][method]}", bg=CARD2, fg=MUTED,
                         font=("Helvetica Neue", 10, "bold"), padx=8, pady=2)
            p.pack(side="left", padx=2)
            self.pills[method] = p

    def build_right(self):
        right = tk.Frame(self, bg=BG, width=390)
        right.grid(row=0, column=2, sticky="ns", padx=(7, 14), pady=14)
        right.grid_propagate(False)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        c = self.card(right)
        c.grid(row=0, column=0, sticky="ew")
        self.pseudo_title = tk.Label(c, text="", bg=CARD, fg=MUTED, font=("Helvetica Neue", 10, "bold"), anchor="w")
        self.pseudo_title.pack(fill="x", padx=12, pady=(10, 4))
        self.pseudo = tk.Text(c, height=10, bg=CARD, fg=TEXT, font=MONO_S, relief="flat", wrap="none",
                              highlightthickness=0, padx=8, pady=2, cursor="arrow")
        self.pseudo.pack(fill="x", padx=6, pady=(0, 10))
        self.pseudo.tag_configure("cur", background=ACCENT_D, foreground="#ffffff")
        self.pseudo.tag_configure("num", foreground=MUTED_D)

        c = self.card(right, "Step log")
        c.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.logbox = tk.Text(c, bg=CARD, fg=TEXT, font=("Helvetica Neue", 11), relief="flat", wrap="word",
                              highlightthickness=0, padx=10, pady=4, cursor="arrow", spacing3=3)
        self.logbox.pack(fill="both", expand=True, padx=2, pady=(0, 8))
        self.logbox.tag_configure("hdr", foreground=ACCENT, font=("Helvetica Neue", 11, "bold"), spacing1=8)
        for k, col in KIND_COLOR.items():
            self.logbox.tag_configure(k, foreground=col)
        self.logbox.config(state="disabled")

    # ------------------------------------------------------------ text panels
    def set_pseudo(self, op):
        self.cur_op = op
        lines = self.q.PSEUDO.get(op, [])
        label = next((l for l, m, _ in self.meta["ops"] if m == op), op)
        self.pseudo_title.config(text=f"PSEUDOCODE - {label.upper()}")
        self.pseudo.config(state="normal", height=max(len(lines), 4))
        self.pseudo.delete("1.0", "end")
        for i, line in enumerate(lines):
            self.pseudo.insert("end", f"{i + 1:>2}  ", "num")
            self.pseudo.insert("end", line + "\n")
        self.pseudo.config(state="disabled")
        for m, p in self.pills.items():
            p.config(bg=ACCENT_D if m == op else CARD2, fg=TEXT if m == op else MUTED)

    def mark_line(self, line):
        self.pseudo.tag_remove("cur", "1.0", "end")
        if line is not None:
            self.pseudo.tag_add("cur", f"{line + 1}.0", f"{line + 1}.end+1c")

    def log(self, kind, text):
        self.logbox.config(state="normal")
        self.logbox.insert("end", text + "\n", kind)
        self.logbox.see("end")
        self.logbox.config(state="disabled")

    # ------------------------------------------------------------ queue control
    def new_queue(self):
        try:
            n = max(2, min(12, int(self.cap_var.get())))
        except ValueError:
            n = 6
        self.cap_var.set(str(n))
        self.pause()
        self.q = self.cls(n)
        self.steps, self.idx, self.logged = [], -1, -1
        self.pre = self.prev_snap = self.cur_snap = self.q.snapshot()
        self.mark_line(None)
        self.step_lbl.config(text="No operation yet")
        self.log("hdr", f"New {self.cls.TITLE} with capacity {n}.")
        self.update_stats(self.cur_snap)
        self.render()

    def clear(self):
        self.pause()
        self.q.reset()
        self.steps, self.idx, self.logged = [], -1, -1
        self.pre = self.prev_snap = self.cur_snap = self.q.snapshot()
        self.mark_line(None)
        self.step_lbl.config(text="No operation yet")
        self.log("hdr", "Queue cleared.")
        self.update_stats(self.cur_snap)
        self.render()

    def read_inputs(self, need):
        raw = self.val.get().strip()
        if need and not raw:
            self.flash("Type a value in the Value box first.")
            return None
        if len(raw) > 6:
            self.flash("Keep values short (6 characters max) so they fit in the boxes.")
            return None
        if need == "vp":
            try:
                return raw, int(self.pri.get())
            except ValueError:
                self.flash("Priority must be a whole number (1 = most urgent).")
                return None
        return (raw,) if need else ()

    def flash(self, text):
        self.note = text
        self.render()
        self.after(2600, self._clear_note)

    def _clear_note(self):
        self.note = None
        self.render()

    def exec(self, method, need, args=None, animate=True):
        if self.cls is LinearQueue:
            self.q.reset_on_empty = self.reset_opt.get()
        if args is None:
            args = self.read_inputs(need)
            if args is None:
                return
        self.finish_current()
        self.pre = self.q.snapshot()
        steps, ret = self.q.run(method, *args)
        self.set_pseudo(method)
        label = next((l for l, m, _ in self.meta["ops"] if m == method), method)
        argtxt = ", ".join(str(a) for a in args)
        self.log("hdr", f">> {label}({argtxt})")
        self.steps, self.idx, self.logged = steps, -1, -1
        self.goto(0)
        if self.auto.get() and len(steps) > 1:
            self.playing = True
            self.play_btn.config(text="Pause")
            self._job = self.after(self.delay(), self.auto_step)

    def finish_current(self):
        """Jump any running operation to its last step so a new one starts from the final state."""
        self.pause()
        if self.steps and self.idx < len(self.steps) - 1:
            self.goto(len(self.steps) - 1, animate=False)

    def random_fill(self):
        self.finish_current()
        added = 0
        for _ in range(self.q.cap // 2 + 1):
            v = random.randint(1, 99)
            if self.cls is PriorityQueue:
                _, r = self.q.run("enqueue", v, random.randint(1, 5))
            elif self.cls is Deque:
                _, r = self.q.run(random.choice(["insert_front", "insert_rear"]), v)
            else:
                _, r = self.q.run("enqueue", v)
            added += r is not None
        self.steps, self.idx = [], -1
        self.pre = self.prev_snap = self.cur_snap = self.q.snapshot()
        self.mark_line(None)
        self.step_lbl.config(text="No operation yet")
        self.log("hdr", f"Random fill: inserted {added} values.")
        self.update_stats(self.cur_snap)
        self.render()

    def demo(self):
        cap = self.meta["demo_cap"]
        self.cap_var.set(str(cap))
        self.new_queue()
        run = lambda op, *a: self.q.run(op, *a)
        if self.cls is LinearQueue:
            self.reset_opt.set(False)
            self.q.reset_on_empty = False
            for v in (11, 22, 33, 44, 55):
                run("enqueue", v)
            for _ in range(3):
                run("dequeue")
            final = ("enqueue", "v", ("99",))
        elif self.cls is CircularQueue:
            for v in (11, 22, 33, 44, 55):
                run("enqueue", v)
            for _ in range(3):
                run("dequeue")
            final = ("enqueue", "v", ("77",))
        elif self.cls is PriorityQueue:
            for v, p in (("x", 5), ("y", 1), ("z", 3)):
                run("enqueue", v, p)
            final = ("enqueue", "vp", ("w", 2))
        else:
            for v in (10, 20, 30):
                run("insert_rear", v)
            final = ("insert_front", "v", ("5",))
        self.pre = self.prev_snap = self.cur_snap = self.q.snapshot()
        self.update_stats(self.cur_snap)
        self.render()
        self.log("hdr", self.meta["demo_note"])
        self.exec(final[0], final[1], args=final[2])

    # ------------------------------------------------------------ playback
    def delay(self):
        return int(1100 / self.speed.get())

    def toggle_play(self):
        if self.playing:
            self.pause()
            return
        if not self.steps:
            return
        if self.idx >= len(self.steps) - 1:
            self.goto(0)
        self.playing = True
        self.play_btn.config(text="Pause")
        self._job = self.after(self.delay(), self.auto_step)

    def pause(self):
        self.playing = False
        self.play_btn.config(text="Play")
        if self._job:
            self.after_cancel(self._job)
            self._job = None

    def auto_step(self):
        self._job = None
        if not self.playing:
            return
        if self.idx < len(self.steps) - 1:
            self.goto(self.idx + 1)
            self._job = self.after(self.delay(), self.auto_step)
        else:
            self.pause()

    def goto(self, i, animate=True):
        if not self.steps:
            return
        i = max(0, min(len(self.steps) - 1, i))
        self.prev_snap = self.steps[i - 1].snap if i > 0 else self.pre
        self.idx = i
        s = self.steps[i]
        self.cur_snap = s.snap
        self.mark_line(s.line)
        self.step_lbl.config(text=f"Step {i + 1} / {len(self.steps)}")
        while self.logged < i:
            self.logged += 1
            st = self.steps[self.logged]
            self.log(st.kind, f"{self.logged + 1}. {st.msg}")
        self.update_stats(s.snap)
        self.start_tween(animate)

    def start_tween(self, animate):
        if self._tween:
            self.after_cancel(self._tween)
            self._tween = None
        if not animate:
            self.t = 1.0
            self.render()
            return
        self.t = 0.0
        self._dur = min(0.55, self.delay() / 1000 * 0.7)
        self._tick()

    def _tick(self):
        self.t = min(1.0, self.t + 0.016 / self._dur)
        self.render()
        self._tween = self.after(16, self._tick) if self.t < 1.0 else None

    def update_stats(self, snap):
        n = len(snap["live"])
        self.stat["size"].set(str(n))
        self.stat["cap"].set(str(snap["cap"]))
        self.stat["front"].set(str(snap["front"]))
        self.stat["rear"].set(str(snap["rear"]))
        self.stat["free"].set(str(snap["cap"] - n))
        wasted = 0
        if self.cls is LinearQueue and snap["front"] > 0:
            wasted = snap["front"]
        elif self.cls is LinearQueue and snap["front"] == -1:
            wasted = 0
        self.wasted_lbl.config(text=f"{wasted} slot(s) wasted" if wasted else "")

    # ------------------------------------------------------------ drawing
    def render(self):
        c = self.canvas
        c.delete("all")
        W, H = c.winfo_width(), c.winfo_height()
        if W < 50 or H < 50:
            return
        snap, prev = self.cur_snap, self.prev_snap
        step = self.steps[self.idx] if self.steps and 0 <= self.idx < len(self.steps) else None
        e = ease(self.t)
        if self.note:
            self.banner(W, self.note, "err")
        elif step:
            self.banner(W, step.msg, step.kind)
        else:
            self.banner(W, "Ready - choose an operation on the left.", "info")
        if self.view.get() == "ring":
            self.draw_ring(c, W, H, snap, prev, step, e)
        else:
            self.draw_row(c, W, H, snap, prev, step, e)

    def banner(self, W, text, kind):
        c = self.canvas
        col = KIND_COLOR.get(kind, TEXT)
        t = c.create_text(W / 2, 20, text=text, fill=col, font=("Helvetica Neue", 13, "bold"),
                          width=W - 140, justify="center", anchor="n")
        x1, y1, x2, y2 = c.bbox(t)
        r = c.create_polygon(rr(x1 - 18, y1 - 9, x2 + 18, y2 + 9, 14), smooth=True, fill=CARD, outline=col)
        c.tag_lower(r, t)

    def cell_style(self, i, snap, step, e, pri_col=None):
        cell = snap["cells"][i]
        live = i in snap["live"]
        ev = step.event if step else None
        hl = step.hl if step else frozenset()
        if cell is None:
            return BG2, BORDER, MUTED_D, (4, 3), 2
        if not live:
            return BG2, MUTED_D, MUTED_D, (4, 3), 2
        fill, out, fg, dash, w = ACCENT_D, pri_col or ACCENT, TEXT, None, 2
        if ev and ev[0] == "write" and ev[1] == i:
            fill, out = mix(GREEN_D, ACCENT_D, e), GREEN
        if i in hl:
            out, w = AMBER, 3
        return fill, out, fg, dash, w

    # ---------- row view
    def draw_row(self, c, W, H, snap, prev, step, e):
        n = snap["cap"]
        cw = min(96, (W - 110) / n)
        ch = max(54, min(80, cw * 0.82))
        x0 = (W - n * cw) / 2
        yc = 100 + (H - 100) / 2
        top = yc - ch / 2 - 6
        cx = lambda i: x0 + (i + 0.5) * cw
        ev = step.event if step else None
        for i in range(n):
            cell = snap["cells"][i]
            pcol = None
            if self.cls is PriorityQueue and cell:
                pcol = PRI_COLOR.get(cell[1], ACCENT)
            fill, out, fg, dash, w = self.cell_style(i, snap, step, e, pcol)
            dx = dy = 0
            if ev and ev[0] == "write" and ev[1] == i:
                dy = -(1 - e) * 70
            if ev and ev[0] == "shift" and ev[2] == i:
                dx = (ev[1] - ev[2]) * cw * (1 - e)
            xa, xb = x0 + i * cw + 5 + dx, x0 + (i + 1) * cw - 5 + dx
            c.create_polygon(rr(xa, top + dy, xb, top + ch + dy, 12), smooth=True, fill=fill, outline=out,
                             width=w, dash=dash)
            if cell:
                size = 18 if len(str(cell[0])) <= 3 else 13
                c.create_text((xa + xb) / 2, top + dy + ch / 2 - (7 if cell[1] is not None else 0),
                              text=str(cell[0]), fill=fg, font=("Helvetica Neue", size, "bold"))
                if cell[1] is not None:
                    c.create_text((xa + xb) / 2, top + dy + ch - 17, text=f"p = {cell[1]}",
                                  fill=pcol or MUTED, font=("Helvetica Neue", 10, "bold"))
            c.create_text(cx(i), top + ch + 16, text=str(i), fill=MUTED, font=MONO_S)
        # wasted-slots bracket (linear queue weakness)
        if self.cls is LinearQueue and snap["front"] > 0:
            xa, xb = x0 + 5, x0 + snap["front"] * cw - 5
            y = top + ch + 32
            c.create_line(xa, y, xb, y, fill=AMBER, width=2)
            c.create_text((xa + xb) / 2, y + 12, text="free but wasted", fill=AMBER, font=("Helvetica Neue", 10, "bold"))
        # pointers
        def px(idx):
            return max(x0 - 30, 50) if idx < 0 else cx(idx)
        fa, fb = px(prev["front"]), px(snap["front"])
        ra, rb = px(prev["rear"]), px(snap["rear"])
        fx, rx = fa + (fb - fa) * e, ra + (rb - ra) * e
        self.pointer(c, rx, top - 8, "REAR", snap["rear"], PINK, down=True)
        self.pointer(c, fx, top + ch + 52, "FRONT", snap["front"], CYAN, down=False)
        self.fly(c, ev, e, lambda i: (cx(i), top + ch / 2), lambda i: (cx(i), top - 70), cw)

    def pointer(self, c, x, y, label, idx, col, down):
        if down:      # triangle pointing down, tip at y
            c.create_polygon(x - 9, y - 14, x + 9, y - 14, x, y, fill=col, outline="")
            c.create_text(x, y - 30, text=f"{label} = {idx}", fill=col, font=("Helvetica Neue", 12, "bold"))
        else:         # triangle pointing up, tip at y
            c.create_polygon(x - 9, y + 14, x + 9, y + 14, x, y, fill=col, outline="")
            c.create_text(x, y + 30, text=f"{label} = {idx}", fill=col, font=("Helvetica Neue", 12, "bold"))

    def fly(self, c, ev, e, src, dst, cw):
        """The removed value floats away and shrinks."""
        if not ev or ev[0] != "remove":
            return
        (x1, y1), (x2, y2) = src(ev[1]), dst(ev[1])
        x, y = x1 + (x2 - x1) * e, y1 + (y2 - y1) * e
        s = max(0.0, 1 - 0.75 * e) * min(cw, 90) * 0.8
        c.create_polygon(rr(x - s / 2, y - s * 0.35, x + s / 2, y + s * 0.35, 10), smooth=True,
                         fill=CYAN, outline="")
        c.create_text(x, y, text=str(ev[2]), fill=BG, font=("Helvetica Neue", max(8, int(14 * (1 - .5 * e))), "bold"))
        c.create_text(x, y - s * 0.35 - 12, text="out", fill=CYAN, font=("Helvetica Neue", 10, "bold"))

    # ---------- ring view
    def draw_ring(self, c, W, H, snap, prev, step, e):
        n = snap["cap"]
        cx0, cy0 = W / 2, 100 + (H - 100) / 2 + 6
        room = (H - 100) / 2 - 6 - 46          # radial space for ring + node + pointer label
        R = max(40, min(W * 0.3, room * 0.78))
        r = max(12, min(38, R * math.sin(math.pi / n) * 0.88, room - R))
        ang = lambda f: -math.pi / 2 + 2 * math.pi * f / n
        pos = lambda f, rad=R: (cx0 + rad * math.cos(ang(f)), cy0 + rad * math.sin(ang(f)))
        ev = step.event if step else None
        c.create_oval(cx0 - R, cy0 - R, cx0 + R, cy0 + R, outline=BORDER, width=2, dash=(2, 6))
        for i in range(n):
            x, y = pos(i)
            fill, out, fg, dash, w = self.cell_style(i, snap, step, e)
            rad = r * (0.35 + 0.65 * e) if ev and ev[0] == "write" and ev[1] == i else r
            c.create_oval(x - rad, y - rad, x + rad, y + rad, fill=fill, outline=out, width=w, dash=dash)
            cell = snap["cells"][i]
            c.create_text(x, y - rad * 0.55, text=str(i), fill=MUTED, font=("Menlo", 9))
            if cell:
                size = 16 if len(str(cell[0])) <= 3 else 11
                c.create_text(x, y + rad * 0.12, text=str(cell[0]), fill=fg, font=("Helvetica Neue", size, "bold"))
        n_live = len(snap["live"])
        c.create_text(cx0, cy0 - 10, text=f"{n_live} / {n}", fill=TEXT, font=("Helvetica Neue", 22, "bold"))
        c.create_text(cx0, cy0 + 14, text="elements", fill=MUTED, font=("Helvetica Neue", 10))

        def idx_at(a, b):
            if a < 0 or b < 0:
                return b
            d = ((b - a + n / 2) % n) - n / 2
            return a + d * e
        for key, col, label, inside in (("rear", PINK, "REAR", False), ("front", CYAN, "FRONT", True)):
            b = snap[key]
            if b < 0:
                continue
            f = idx_at(prev[key], b)
            a_ = ang(f)
            ux, uy = math.cos(a_), math.sin(a_)
            sgn = -1 if inside else 1
            tip = R + sgn * (r + 4)
            base = tip + sgn * 14
            px_, py_ = cx0 + ux * base, cy0 + uy * base
            vx, vy = -uy * 9, ux * 9
            c.create_polygon(cx0 + ux * tip, cy0 + uy * tip, px_ + vx, py_ + vy, px_ - vx, py_ - vy,
                             fill=col, outline="")
            lx, ly = cx0 + ux * (tip + sgn * 32), cy0 + uy * (tip + sgn * 32)
            c.create_text(lx, ly, text=f"{label}={b}", fill=col, font=("Helvetica Neue", 11, "bold"))
        if snap["front"] < 0:
            c.create_text(cx0, cy0 + 40, text="front = rear = -1", fill=MUTED, font=MONO_S)
        self.fly(c, ev, e, lambda i: pos(i), lambda i: (cx0, cy0 - 62), 70)


# ---------------------------------------------------------------- app
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Queue Simulator - DAA Prototype")
        self.geometry("1380x860")
        self.minsize(1180, 760)
        self.configure(bg=BG)
        self.style()
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=18, pady=(14, 0))
        tk.Label(head, text="Queue Simulator", bg=BG, fg=TEXT, font=("Helvetica Neue", 24, "bold")).pack(side="left")
        tk.Label(head, text="   FIFO  -  insert at REAR  -  delete from FRONT", bg=BG, fg=MUTED,
                 font=("Helvetica Neue", 12)).pack(side="left", pady=(10, 0))
        tk.Label(head, text="Design & Analysis of Algorithms", bg=BG, fg=MUTED_D,
                 font=("Helvetica Neue", 11)).pack(side="right", pady=(10, 0))
        self.nb = ttk.Notebook(self, style="Q.TNotebook")
        self.nb.pack(fill="both", expand=True, pady=(8, 0))
        self.panels = []
        for cls, title in TAB_TITLES:
            p = QueuePanel(self.nb, cls)
            self.nb.add(p, text=title)
            self.panels.append(p)

    def style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Q.TNotebook", background=BG, borderwidth=0, tabmargins=(18, 4, 0, 0))
        s.configure("Q.TNotebook.Tab", background=CARD, foreground=MUTED, padding=(14, 8),
                    font=("Helvetica Neue", 12, "bold"), borderwidth=0)
        s.map("Q.TNotebook.Tab", background=[("selected", ACCENT_D)], foreground=[("selected", TEXT)])
        s.configure("Q.TCheckbutton", background=CARD, foreground=TEXT, font=SANS, focuscolor=CARD)
        s.map("Q.TCheckbutton", background=[("active", CARD)])
        s.configure("Q.TRadiobutton", background=CARD, foreground=TEXT, font=SANS, focuscolor=CARD)
        s.map("Q.TRadiobutton", background=[("active", CARD)])
        s.configure("Q.Horizontal.TScale", background=CARD, troughcolor=BG2)


def selftest():
    app = App()
    app.update()
    for p in app.panels:
        for _, method, need in p.meta["ops"]:
            args = ("7", 2) if need == "vp" else ("7",) if need else ()
            for view in p.meta["views"]:
                p.view.set(view)
                p.auto.set(False)
                p.exec(method, need, args=args)
                for i in range(len(p.steps)):
                    p.goto(i, animate=False)
                p.t = 0.4
                p.render()
        p.demo()
        p.pause()
        p.goto(len(p.steps) - 1, animate=False)
        p.random_fill()
        p.clear()
    app.update()
    print("selftest OK")
    app.destroy()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        App().mainloop()
