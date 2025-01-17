from __future__ import annotations
from dataclasses import asdict
from threading import Thread
from time import sleep
import tkinter as tk
from tkinter import BOTH, DISABLED, NORMAL, CENTER
from tkinter import messagebox
from typing import TYPE_CHECKING
from win32api import EnumDisplayMonitors

import ttkbootstrap as ttk

from captol.utils.const import ICON_FILE
from captol.utils.path import unique_str
from captol.frontend.subframe import TransparentWindow
from captol.backend.data import Rectangle
from captol.backend.extraction import ImageBuffer

if TYPE_CHECKING:
    from captol.frontend.extracttab import ExtractTab
    from captol.backend.data import AreaDB, Environment
    from captol.backend.extraction import Clipper, ImageCounter


def get_expanded_screen_info() -> tuple[int]:
    xmin, ymin, xmax, ymax = 0, 0, 0, 0
    for winfo in EnumDisplayMonitors():
        x1, y1, x2, y2 = winfo[-1]
        xmin = min(x1, xmin)
        ymin = min(y1, ymin)
        xmax = max(x2, xmax)
        ymax = max(y2, ymax)
    return xmin, ymin, xmax-xmin, ymax-ymin


class ClipFrame(ttk.Frame):

    def __init__(
        self, root: ttk.Frame, parent: ExtractTab, env: Environment,
        clipper: Clipper, counter: ImageCounter
    ) -> None:
        super().__init__(root)
        self.root = root
        self.parent = parent
        self.env = env
        self.clipper = clipper
        self.counter = counter
        self.thread = None
        self.thread_alive = False
        self.var_clipmode = tk.IntVar()  # 1: manual, 2: auto
        self.var_areaname = tk.StringVar()
        self.imbuffer = ImageBuffer(env)
        self.xparentwindow = TransparentWindow(parent=self)
        self._is_showingprev = False

        self._create_widgets()
        self._init_vars()
        self.block_widgets()

    def register_cliparea(self, name: str, rect: Rectangle) -> None:
        self.clipper.register(rect)
        self.var_areaname.set(name)
        self.xparentwindow.resize(**asdict(rect))

    def block_widgets(self) -> None:
        for widget in self.winfo_children():
            try:
                widget['state'] = DISABLED
            except tk.TclError:
                pass

    def release_widgets(self) -> None:
        for widget in self.winfo_children():
            try:
                widget['state'] = NORMAL
            except tk.TclError:
                pass

    def is_activated_byname(self, name: str) -> bool:
        if self.fold_button['state'] == DISABLED:
            return False
        if self.var_areaname.get() == name:
            return True
        return False

    def _create_widgets(self) -> None:
        ttk.Button(
            self, text="✂", bootstyle='success-button',
            command=self._on_camera_clicked).place(x=10, y=2, width=60)
        area_button = self.area_button = ttk.Button(
            self, textvariable=self.var_areaname,
            bootstyle='secondary-outline-toolbutton',
            command=self._switch_preview)
        area_button.place(x=80, y=2, width=200)
        ttk.Radiobutton(
            self, text="Auto", variable=self.var_clipmode,
            bootstyle='danger-roundtoggle',
            command=self._on_auto_clicked).place(x=300, y=10)
        fold_button = self.fold_button = ttk.Button(
            self, text="▲", bootstyle='secondary-outline-button',
            command=self._on_fold_clicked)
        fold_button.place(x=400, y=2, width=45)

    def _init_vars(self) -> None:
        self.var_clipmode.set(2)
        self.var_areaname.set("( Not set )")

    def _on_camera_clicked(self) -> None:
        if self.clipper.area is None:
            return
        self._normal_save()

    def _on_fold_clicked(self) -> None:
        self.parent.hide()
        self.fold_button['text'] = "▼"
        self.fold_button['command'] = self._on_unfold_clicked

    def _on_unfold_clicked(self) -> None:
        self.parent.show()
        self.fold_button['text'] = "▲"
        self.fold_button['command'] = self._on_fold_clicked

    def _on_auto_clicked(self) -> None:
        if not self.thread_alive:
            self._start_autoclip()
        else:
            self._end_autoclip()

    def _switch_preview(self) -> None:
        self.parent.xparentwindow.hide()

        if self._is_showingprev:
            self.area_button.state(['!pressed'])
            self.xparentwindow.hide()
            self._is_showingprev = False
        else:
            self.area_button.state(['pressed'])
            self.xparentwindow.preview()
            self._is_showingprev = True

    def _start_autoclip(self) -> None:
        def _target():
            while self.thread_alive:
                self._noduplicate_save()
                sleep(self.env.auto_clip_interval)

        def _run_thread():
            self.thread_alive = True
            thread = self.thread = Thread(target=_target)
            thread.start()

        if messagebox.askyesno(
            "Autoclip", "Do you want to enable Autoclip?"):
            self.parent.block_widgets()
            self.area_button.state(['disabled'])
            self.root.after(500, _run_thread)  # messageboxをキャプチャしないように
        else:
            self.var_clipmode.set(2)

    def _end_autoclip(self) -> None:
        self.var_clipmode.set(2)
        if self.thread_alive:
            if self.thread is not None:
                self.thread_alive = False
                self.thread.join()
                self.thread = None
            messagebox.showinfo("Autoclip", "Autoclip stopped.")
            self.parent.release_widgets()
            self.area_button.state(['!disabled'])

    def _normal_save(self) -> None:
        self._extract()
        self._store()

    def _noduplicate_save(self) -> None:
        self._extract()
        for i in range(self.env.image_duplication_check_steps):
            if self.imbuffer.compare_similarity(i+1):
                self.imbuffer.release()
                return
        self._store()

    def _extract(self) -> None:
        self.xparentwindow.hide_all()
        image = self.clipper.clip()
        self.imbuffer.hold(image)

    def _store(self) -> None:
        name = self.counter.next_savepath()
        self.imbuffer.save(name)
        self.xparentwindow.flash()
        self.counter.up(1)


class EditDialog(ttk.Frame):

    def __init__(
        self, parent: ExtractTab, areadb: AreaDB, name: str = None
    ) -> None:
        root = self.root = tk.Toplevel(parent)
        root.withdraw()
        super().__init__(root)
        self.parent = parent
        self.areadb = areadb
        self.init_name = name
        self.name = tk.StringVar()
        self.x = tk.IntVar()
        self.y = tk.IntVar()
        self.w = tk.IntVar()
        self.h = tk.IntVar()
        self.xparentwindow = TransparentWindow(parent=self)

        self._setup_root()
        self._create_widgets()
        self._init_vars()

    def block_widgets(self) -> None:
        for widget in self.winfo_children():
            try:
                if widget.winfo_name() == '!button3':
                    continue
                widget['state'] = DISABLED
            except tk.TclError:
                pass

    def release_widgets(self) -> None:
        for widget in self.winfo_children():
            try:
                widget['state'] = NORMAL
            except tk.TclError:
                pass

    def _setup_root(self) -> None:
        try:
            self.root.iconbitmap(ICON_FILE)
        except FileNotFoundError:
            pass
        self.root.title("Edit")
        self.root.geometry("460x250")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.protocol('WM_DELETE_WINDOW', self._on_cancel)
        self.root.grab_set()
        self.root.deiconify()

    def _create_widgets(self) -> None:
        ttk.Label(self, text="Area name: ").place(x=10, y=20)
        ttk.Entry(
            self,
            textvariable=self.name).place(x=130, y=20, width=320, height=37)
        ttk.LabelFrame(self, text="Area").place(
            x=10, y=60, width=440, height=130)
        ttk.Button(
            self, text="Direct\nDraw", bootstyle='warning-button',
            command=self._on_direct_draw).place(
                x=30, y=95, width=90, height=80)
        ttk.Label(self, text="x:").place(x=150, y=95)
        spb_x = ttk.Spinbox(
            self, textvariable=self.x, from_=-9999, to=9999,
            command=self._on_spb_changed)
        spb_x.place(x=180, y=95, width=80)
        ttk.Label(self, text="width:").place(x=280, y=95)
        spb_w = ttk.Spinbox(
            self, textvariable=self.w, from_=-9999, to=9999,
            command=self._on_spb_changed)
        spb_w.place(x=350, y=95, width=80)
        ttk.Label(self, text="y:").place(x=150, y=140)
        spb_y = ttk.Spinbox(
            self, textvariable=self.y, from_=-9999, to=9999,
            command=self._on_spb_changed)
        spb_y.place(x=180, y=140, width=80)
        ttk.Label(self, text="height:").place(x=280, y=140)
        spb_h = ttk.Spinbox(
            self, textvariable=self.h, from_=-9999, to=9999,
            command=self._on_spb_changed)
        spb_h.place(x=350, y=140, width=80)
        ttk.Button(
            self, text="OK", command=self._on_ok,
            bootstyle='primary-button').place(x=40, y=200, width=160)
        ttk.Button(
            self, text="Cancel", command=self._on_cancel,
            bootstyle='primary-outline-button').place(x=260, y=200, width=160)
        spb_x.bind('<KeyRelease>', self._on_spb_changed)
        spb_w.bind('<KeyRelease>', self._on_spb_changed)
        spb_y.bind('<KeyRelease>', self._on_spb_changed)
        spb_h.bind('<KeyRelease>', self._on_spb_changed)
        self.pack(fill=BOTH, expand=True)

    def _init_vars(self) -> None:
        name = self.init_name
        if self.areadb.has_name(name):
            x, y, w, h = asdict(self.areadb.get(name)).values()
        else:
            x, y, w, h = 100, 200, 400, 300
            name = unique_str("New", self.areadb.namelist)

        self.x.set(x)
        self.y.set(y)
        self.w.set(w)
        self.h.set(h)
        self.name.set(name)
        self.xparentwindow.resize(x, y, w, h)
        self.xparentwindow.preview()

    def _on_direct_draw(self) -> None:
        Drawer(self, self.xparentwindow, self.x, self.y, self.w, self.h)
        self.xparentwindow.hide()

    def _on_spb_changed(self, event: tk.Event = None) -> None:
        try:
            x, y, w, h = self.x.get(), self.y.get(), self.w.get(), self.h.get()
        except tk.TclError:  # deleteで全部消すとget()で "" (str)が返る．
            return
        self.xparentwindow.resize(x, y, w, h)

    def _on_ok(self) -> None:
        name = self.name.get()
        try:
            x, y, w, h = self.x.get(), self.y.get(), self.w.get(), self.h.get()
        except tk.TclError:
            messagebox.showerror(
                "Editor", "Only numbers are acceptable.")
            return

        if not self._validate(name, x, y, w, h):
            return

        if name != self.init_name:
            if self.areadb.has_name(name):
                if not messagebox.askyesno(
                    "Editor",
                    "The same name already exists."
                    "Are you sure to overwrite it?"):
                    return
            if self.init_name is not None:
                self.areadb.delete(self.init_name)

        rect = Rectangle(x, y, w, h)
        self.areadb.write(name, rect)
        self.areadb.save()
        self.parent.update_listitems(activate_name=name)
        self.parent.update_clipinfo(self.init_name, name, rect)
        self.parent.xparentwindow.resize(x, y, w, h)
        self.parent.xparentwindow.preview()
        self.root.destroy()

    def _on_cancel(self) -> None:
        if not messagebox.askyesno(
            "Edior", "Do you want to leave? \n(Edits are not saved.)"):
            return
        self.xparentwindow.hide()
        self.parent.xparentwindow.preview()
        self.root.destroy()

    def _validate(self, name: str, x: int, y: int, w: int, h: int) -> bool:
        if name == "":
            messagebox.showerror("Invalid Input", "Area name cannot be blank.")
            return False
        if w < 0 or h < 0:
            messagebox.showerror(
                "Invalid Input", "Width, height must be a positive value.")
            return False
        return True


class Drawer(ttk.Frame):

    def __init__(
        self, parent: EditDialog, xparentwindow: TransparentWindow,
        var_x: tk.IntVar, var_y: tk.IntVar, var_w: tk.IntVar, var_h: tk.IntVar
    ) -> None:
        root = self.root = tk.Toplevel(parent)
        super().__init__(root)
        self.root = root
        self.parent = parent
        self.var_x = var_x
        self.var_y = var_y
        self.var_w = var_w
        self.var_h = var_h
        self.minx = None
        self.miny = None
        self.sx = None
        self.sy = None
        self.xparentwindow = xparentwindow

        self._setup_root()
        self._create_widgets()  # iconifyは座標がずれる
        parent.block_widgets()

    def _setup_root(self) -> None:
        self.root.attributes('-alpha', 0.002)
        x, y, w, h = get_expanded_screen_info()
        self.root.geometry(f'{w}x{h}+{x}+{y}')
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        self.minx, self.miny = x, y

    def _create_widgets(self) -> None:
        canvas = self.canvas = tk.Canvas(self, highlightthickness=0)
        canvas.pack(fill=BOTH, expand=True)
        canvas.bind('<ButtonPress-1>', self._on_drag_start)
        canvas.bind('<B1-Motion>', self._on_moving)
        canvas.bind('<ButtonRelease>', self._on_drag_end)
        self.pack(fill=BOTH, expand=True)

    def _on_drag_start(self, event: tk.Event) -> None:
        self.sx = self.minx + event.x
        self.sy = self.miny + event.y
        self.xparentwindow.resize(0, 0, 0, 0)
        self.xparentwindow.preview()

    def _on_moving(self, event: tk.Event) -> None:
        sx, sy = self.sx, self.sy
        cx, cy = self.minx + event.x, self.miny + event.y
        x, y, w, h = min(sx, cx), min(sy, cy), abs(sx-cx), abs(sy-cy)
        self.xparentwindow.resize(x, y, w, h)

    def _on_drag_end(self, event: tk.Event) -> None:
        sx, sy = self.sx, self.sy
        cx, cy = self.minx + event.x, self.miny + event.y
        self.var_x.set(min(sx, cx))
        self.var_y.set(min(sy, cy))
        self.var_w.set(abs(sx-cx))
        self.var_h.set(abs(sy-cy))
        self.parent.release_widgets()
        self.root.destroy()

