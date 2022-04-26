from __future__ import annotations
from ctypes import windll
import tkinter as tk

from captol.frontend.mainframe import Application


def set_high_resolution() -> None:
    windll.shcore.SetProcessDpiAwareness(True)


def run() -> None:
    try:
        set_high_resolution()
    except:
        pass
    root = tk.Tk()
    Application(root)
    root.mainloop()
