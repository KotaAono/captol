from __future__ import annotations
from threading import Thread
import tkinter as tk
from tkinter import BOTH, LEFT, RIGHT, TOP, BOTTOM, Y
from tkinter import ttk
from tkinter import messagebox
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from captol.frontend.clipping import ClipFrame, EditDialog
    from captol.frontend.extracttab import ExtractTab
    from captol.frontend.mergetab import MergeTab


class TransparentWindow(tk.Frame):
    roots: list[tk.Toplevel] = list()

    def __init__(self, parent: ExtractTab | ClipFrame | EditDialog) -> None:
        root = self.root = tk.Toplevel(parent)
        super().__init__(root, bg='white')
        self.parent = parent
        self.markframe = None
        self.prev_name = None

        self._setup_root()
        self._create_widgets()
        self.hide()

    def hide(self) -> None:
        self.root.withdraw()

    def hide_all(self) -> None:
        for root in TransparentWindow.roots:
            try:
                root.withdraw()
            except tk.TclError:
                pass

    def preview(self) -> None:
        self.markframe.pack(fill=BOTH, expand=True)
        self.root.lift()
        self.parent.root.lift()
        self.root.deiconify()

    def flash(self) -> None:
        self.root.withdraw()
        self.markframe.pack_forget()
        self.root.lift()
        self.root.deiconify()
        self.root.after(80, self.root.withdraw)

    def resize(self, x: int, y: int, w: int, h:int) -> None:
        getmetry = f'{w}x{h}+{x}+{y}'
        self.root.geometry(getmetry)

    def _setup_root(self) -> None:
        self.root.attributes('-alpha', 0.2)
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        TransparentWindow.roots.append(self.root)

    def _create_widgets(self) -> None:
        frame = self.markframe = tk.Frame(self, bg='white')
        size_v = 20
        size_h = int(size_v * 1.6)
        size_c = int(size_v * 0.8)
        tk.Label(
            frame, text='◀', font=('', size_h, 'bold'),
            fg='black', bg='white').pack(side=LEFT, fill=Y)
        tk.Label(
            frame, text='▶', font=('', size_h, 'bold'),
            fg='black', bg='white').pack(side=RIGHT, fill=Y)
        tk.Label(
            frame, text='▲', font=('', size_v),
            fg='black', bg='white').pack(side=TOP)
        tk.Label(
            frame, text='▼', font=('', size_v),
            fg='black', bg='white').pack(side=BOTTOM)
        tk.Label(
            frame, text='＋', font=('', size_c),
            fg='black', bg='white').pack(expand=True)
        self.pack(fill=BOTH, expand=True)



class ProgressWindow(ttk.Frame):

    def __init__(self, parent: MergeTab, title: str, text: str) -> None:
        root = self.root = tk.Toplevel(parent)
        super().__init__(root)
        self.parent = parent
        self.title = title
        self.text = text
        self.during_funcs = list()
        self.after_funcs = list()
        self.exc_funcs = list()
        self.final_funcs = list()

        self._setup_root()
        self._create_widget()

    def __enter__(self) -> ProgressWindow:
        return self

    def __exit__(self, *args: Any) -> None:
        self._run()
        self._wait_finish()

    def during(self, func: Callable, *args: Any) -> None:
        self.during_funcs.append(lambda: func(*args))

    def after(self, func: Callable, *args: Any) -> None:
        self.after_funcs.append(lambda: func(*args))

    def final(self, func: Callable, *args: Any) -> None:
        self.final_funcs.append(lambda: func(*args))

    def _setup_root(self) -> None:
        self.root.title(self.title)
        self.root.geometry("460x85")
        self.root.resizable(False, False)
        self.root.grab_set()

    def _create_widget(self) -> None:
        ttk.Label(self, text=self.text).place(x=20, y=20)
        bar = self.bar = ttk.Progressbar(self, mode='indeterminate')
        bar.place(x=20, y=50, width=420)
        self.pack(fill=BOTH, expand=True)

    def _run(self) -> None:
        def _target():
            try:
                self.bar.start(5)
                for func in self.during_funcs:
                    func()
                self.root.destroy()
                messagebox.showinfo(self.title, "Completed!")
                for func in self.after_funcs:
                    func()
            except Exception as e:
                self.bar.stop()
                messagebox.showerror(self.title, e)
            finally:
                self.root.destroy()
                for func in self.final_funcs:
                    func()
        thread = self.thread = Thread(target=_target)
        thread.start()

    def _wait_finish(self) -> None:
        if self.thread.is_alive():
            return self.root.after(100, self._wait_finish)


