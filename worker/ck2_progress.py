#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# CorridorKey 2 for Resolve - progress window
#
# From Creative Video Tips (CVT)
# Created by Chadwick  |  https://creativevideotips.com
# An unofficial plugin around CorridorKey 2.0 by Corridor Digital.
# Licence: CC BY-NC-SA 4.0 with the CorridorKey additional terms (see LICENSE).
#
# Started by the worker for each Process. Reads the worker's JSON event lines
# on stdin and shows the stage, a progress bar, the time left and a Cancel
# button (which stops the worker). Closes itself a few seconds after the end.
#
# Usage: python ck2_progress.py <worker pid> <title>
# ---------------------------------------------------------------------------
from __future__ import annotations

import json
import os
import queue
import signal
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

CHARCOAL, PANEL, TEXT, MUTED, TEAL = "#2b2b2b", "#353535", "#e8e8e8", "#a0a0a0", "#1fa3a3"


def fmt_time(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m} min {s:02d} s"
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min"


class Estimator:
    """Time left from the frames finished so far (they arrive in bursts, one
    burst per window, so the rate is taken from the first finished frame)."""

    def __init__(self) -> None:
        self.first_t = None
        self.first_done = 0

    def update(self, t: float, done: int, total: int) -> str:
        if self.first_t is None:
            self.first_t, self.first_done = t, done
            return ""
        if done <= self.first_done or t <= self.first_t:
            return ""
        rate = (t - self.first_t) / (done - self.first_done)
        return "About " + fmt_time(rate * (total - done)) + " left"


def main() -> int:
    worker_pid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    title = sys.argv[2] if len(sys.argv) > 2 else "CorridorKey 2"

    events: queue.Queue = queue.Queue()

    def reader() -> None:
        for line in sys.stdin:
            try:
                events.put(json.loads(line))
            except ValueError:
                pass
        events.put({"event": "eof"})

    threading.Thread(target=reader, daemon=True).start()

    root = tk.Tk()
    # Hidden until it is built and centred: Tk first draws a new window in the
    # top-left corner, which flashed there for a moment (0.15-0.25).
    root.withdraw()
    root.title(title)
    root.configure(bg=CHARCOAL)
    root.resizable(False, False)
    root.attributes("-topmost", True)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("CK.Horizontal.TProgressbar", troughcolor=PANEL, background=TEAL,
                    bordercolor=PANEL, lightcolor=TEAL, darkcolor=TEAL, thickness=14)

    frame = tk.Frame(root, bg=CHARCOAL, padx=20, pady=16)
    frame.pack(fill="both", expand=True)
    tk.Label(frame, text="CorridorKey 2", bg=CHARCOAL, fg=TEAL,
             font=("Helvetica", 15, "bold")).pack(anchor="w")
    stage = tk.Label(frame, text="Starting...", bg=CHARCOAL, fg=TEXT, font=("Helvetica", 13))
    stage.pack(anchor="w", pady=(8, 6))
    bar = ttk.Progressbar(frame, style="CK.Horizontal.TProgressbar", length=380,
                          mode="indeterminate", maximum=100)
    bar.pack(fill="x")
    bar.start(12)
    left = tk.Label(frame, text="", bg=CHARCOAL, fg=MUTED, font=("Helvetica", 11))
    left.pack(anchor="w", pady=(6, 10))
    tk.Frame(frame, bg="#4a4a4a", height=1).pack(fill="x", pady=(0, 10))
    row = tk.Frame(frame, bg=CHARCOAL)
    row.pack(fill="x")
    # The model is Corridor Digital's; only the plugin is ours.
    tk.Label(row, text="KolorKlinic", bg=CHARCOAL, fg=MUTED,
             font=("Helvetica", 10)).pack(side="left")

    state = {"finished": False, "determinate": False}

    def cancel() -> None:
        if state["finished"]:
            root.destroy()
            return
        button.enabled = False
        button.config(fg=MUTED)
        stage.config(text="Stopping...")
        if worker_pid > 0:
            try:
                os.kill(worker_pid, signal.SIGTERM)
            except OSError:
                pass

    # Drawn as a label: macOS ignores a tk.Button's colours and drew light
    # text on a white button (0.15-0.21), which was hard to read.
    BUTTON, BUTTON_HOVER = "#4a4a4a", "#5a5a5a"
    button = tk.Label(row, text="Cancel", bg=BUTTON, fg="#ffffff", font=("Helvetica", 12),
                      padx=18, pady=5, cursor="hand2")
    button.pack(side="right")
    button.enabled = True

    def press(_event=None):
        if button.enabled:
            cancel()

    button.bind("<Button-1>", press)
    button.bind("<Enter>", lambda _e: button.config(bg=BUTTON_HOVER if button.enabled else BUTTON))
    button.bind("<Leave>", lambda _e: button.config(bg=BUTTON))
    root.protocol("WM_DELETE_WINDOW", cancel)

    est = Estimator()
    started = time.time()

    def finish(text: str, ok: bool) -> None:
        state["finished"] = True
        bar.stop()
        bar.config(mode="determinate", value=100 if ok else bar["value"])
        stage.config(text=text)
        left.config(text="")
        button.enabled = True
        button.config(text="Close", fg="#ffffff")
        root.after(4000 if ok else 15000, root.destroy)

    def poll() -> None:
        try:
            while True:
                e = events.get_nowait()
                kind = e.get("event")
                if state["finished"] and kind != "eof":
                    continue
                if kind == "plan":
                    n = e.get("chunks")
                    stage.config(text=f"Preparing {e.get('frames')} frames in {n} "
                                      f"{'chunk' if n == 1 else 'chunks'} of {e.get('window')}")
                elif kind == "status":
                    msg = str(e.get("message", ""))
                    stage.config(text=msg[:1].upper() + msg[1:])
                elif kind == "progress":
                    done, total = int(e.get("done", 0)), max(1, int(e.get("total", 1)))
                    if not state["determinate"]:
                        bar.stop()
                        bar.config(mode="determinate")
                        state["determinate"] = True
                    bar.config(value=100.0 * done / total)
                    stage.config(text=f"Keying frame {done} of {total} "
                                      f"(chunk {e.get('chunk')} of {e.get('chunks')})")
                    left.config(text=est.update(float(e.get("t", time.time() - started)), done, total))
                elif kind == "done":
                    n = e.get("chunks")
                    finish(f"Done: {e.get('frames')} frames in {fmt_time(float(e.get('seconds', 0)))} "
                           f"({n} {'chunk' if n == 1 else 'chunks'} of {e.get('window')} frames)", True)
                elif kind == "error":
                    finish("Stopped: " + str(e.get("message", "")), False)
                elif kind == "eof":
                    if not state["finished"]:
                        finish("Stopped", False)
        except queue.Empty:
            pass
        root.after(150, poll)

    root.after(150, poll)
    root.update_idletasks()
    w, h = root.winfo_reqwidth(), root.winfo_reqheight()     # the size it will have
    root.geometry(f"+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 3}")
    root.deiconify()                                         # first shown here, centred
    root.lift()
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
