from __future__ import annotations
import tkinter as tk

from .mainframe import Application
from .utils import set_high_resolution


ICONFILE = '../icon/icon.ico'


def run() -> None:
    set_high_resolution()
    root = tk.Tk()
    Application(root)
    root.mainloop()
