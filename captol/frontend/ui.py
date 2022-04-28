from __future__ import annotations
from ctypes import windll
import ttkbootstrap as ttk

from captol.frontend.mainframe import Application


def set_high_resolution() -> None:
    windll.shcore.SetProcessDpiAwareness(True)


def run() -> None:
    try:
        set_high_resolution()
    except:
        pass
    root = ttk.Window()
    Application(root)
    root.mainloop()


r"""Library Fixes

[ttkbootstrap]
File "C:\Users\hnlPublic\anaconda3\envs\appdev38\lib\site-packages\ttkbootstrap\style.py", line 4601, in update_combobox_popdown_style
    +|try:
     |    # set popdown style
     |    popdown = widget.tk.eval(f"ttk::combobox::PopdownWindow {widget}")
     |    widget.tk.call(f"{popdown}.f.l", "configure", *tk_settings)
     |
     |    # set scrollbar style
     |    sb_style = "TCombobox.Vertical.TScrollbar"
     |    widget.tk.call(f"{popdown}.f.sb", "configure", "-style", sb_style)
    +|except:
    +|    pass
"""