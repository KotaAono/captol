from __future__ import annotations
from ctypes import windll
from dataclasses import asdict
from os.path import basename, splitext
from threading import Thread
from time import sleep
import tkinter as tk
from tkinter import BOTH, DISABLED, NORMAL, CENTER, LEFT, RIGHT, TOP, BOTTOM, VERTICAL, Y
from tkinter import ttk
from tkinter import filedialog, messagebox
from typing import Any, Callable
from win32api import EnumDisplayMonitors

from ttkbootstrap import Style

from data import AreaDB, Rectangle, Environment
from extraction import Clipper, ImageCounter, ImageBuffer
from merging import PdfConverter, PassLock


ICONFILE = 'favicon.ico'


def set_high_resolution() -> None:
    windll.shcore.SetProcessDpiAwareness(True)


def get_expanded_screen_info() -> tuple[int]:
    xmin, ymin, xmax, ymax = 0, 0, 0, 0
    for winfo in EnumDisplayMonitors():
        x1, y1, x2, y2 = winfo[-1]
        xmin = min(x1, xmin)
        ymin = min(y1, ymin)
        xmax = max(x2, xmax)
        ymax = max(y2, ymax)
    return xmin, ymin, xmax-xmin, ymax-ymin


def noext_basename(path: str) -> str:
    return splitext(basename(path))[0]


def unique_str(orgstr: str, strlist: list[str]) -> str:
    i = 0
    unistr = orgstr
    while unistr in strlist:
        i += 1
        unistr = f"{orgstr} ({i})"
    return unistr


def shorten(path: str, maxlen: int) -> str:
    path = path.replace('/', '\\')
    dirlist = path.split('\\')
    if len(dirlist) > maxlen:
        return '\\'.join(['...', dirlist[-2], dirlist[-1]])
    return path


def append_ext(path: str, ext: str) -> str:
    if not path.endswith((ext.lower(), ext.upper())):
        return path + ext.lower()
    return path


class Application(ttk.Frame):

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.settingswindow = None
        self.env = Environment()

        self._setup_root()
        self._create_widgets()

    def resize(self, geometry: str) -> None:
        self.root.geometry(geometry)

    def enable_mergetab(self) -> None:
        self.note.tab(1, state=NORMAL)

    def disable_mergetab(self) -> None:
        self.note.tab(1, state=DISABLED)

    def _setup_root(self) -> None:
        try:
            self.root.iconbitmap(ICONFILE)
        except FileNotFoundError:
            pass
        self.root.title("Captol v1.0")
        self.root.attributes('-topmost', True)
        self.root.geometry("460x530-0+0")
        self.root.resizable(False, False)
        self.root = Style(self.env.theme).master

    def _create_widgets(self) -> None:
        note = self.note = ttk.Notebook(self)
        note.root = self
        note.place(x=0, y=10, relwidth=1, height=520)
        note.add(ExtractTab(
            note, parent=self, env=self.env), text="1. Extract")
        note.add(MergeTab(
            note, parent=self, env=self.env), text="2. Merge  ")
        ttk.Button(
            self, text="Settings", style='secondary.Outline.TButton',
            command=self._on_settings_clicked).place(x=360, y=4, width=95)
        self.pack(fill=BOTH, expand=True)

    def _on_settings_clicked(self) -> None:
        if not self._has_opened_settingswindow():
            self.settingswindow = SettingsWindow(parent=self, env=self.env)

    def _has_opened_settingswindow(self) -> bool:
        return self.settingswindow is not None and \
               self.settingswindow.root.winfo_exists()


class ExtractTab(ttk.Frame):

    def __init__(
            self, root: ttk.Notebook, parent: Application,
            env: Environment) -> None:
        super().__init__(root)
        self.root = root
        self.parent = parent
        self.env = env
        self.prevname = None
        self.var_folder = tk.StringVar()
        var_nimages_total = self.var_nimages_total = tk.IntVar()
        var_nimages_today = self.var_nimages_today = tk.IntVar()
        self.var_listitems = tk.StringVar()
        self.var_clipmode = tk.IntVar()
        areadb = self.areadb = AreaDB(env)
        self.clipper = Clipper()
        self.counter = ImageCounter(
            'png', var_nimages_total, var_nimages_today)
        self.xparentwindow = TransparentWindow(parent=root)

        self._create_widgets()
        self._init_vars()
        self._reset_folder_info(env.default_save_folder)
        self._reset_clip_areas(areadb.namelist)

    def shrink(self) -> None:
        self.frame1.pack_forget()
        self.parent.disable_mergetab()
        self.parent.resize("460x110")

    def extend(self) -> None:
        self.frame2.pack_forget()
        self.frame1.pack(fill=BOTH, expand=True)
        self.frame2.pack(fill=BOTH, expand=True)
        self.parent.enable_mergetab()
        self.parent.resize("460x530")

    def block_widgets(self) -> None:
        for widget in self.frame1.winfo_children():
            try:
                widget['state'] = DISABLED
            except tk.TclError:
                pass

    def release_widgets(self) -> None:
        for widget in self.frame1.winfo_children():
            try:
                if widget.winfo_name() == '!entry':
                    widget['state'] = 'readonly'
                else:
                    widget['state'] = NORMAL
            except tk.TclError:
                pass

    def update_listitems(self, activate_name : str = None) -> None:
        self._reset_clip_areas(self.areadb.namelist)
        if activate_name is not None:
            self._unselect_lbitem()
            self._select_lbitem(activate_name)

    def update_clipinfo(
        self, oldname: str, newname: str, newrect: Rectangle) -> None:
        if self.clipframe.is_activated_byname(oldname):
            self.clipframe.register_cliparea(newname, newrect)

    def _create_widgets(self) -> None:
        frame1 = self.frame1 = ttk.Frame(self, height=350)
        frame1.pack(fill=BOTH, expand=True)

        ttk.LabelFrame(
            frame1,
            text="Save folder").place(x=10, y=10, width=435, height=170)
        ttk.Button(
            frame1, text="📁", style='secondary.Outline.TButton',
            command=self._on_folder_clicked).place(x=30, y=50, width=45)
        ttk.Entry(
            frame1, textvariable=self.var_folder,
            state='readonly').place(x=80, y=50, width=345, height=37)
        ttk.Label(frame1, text="Past images:").place(x=30, y=100)
        ttk.Label(
            frame1, textvariable=self.var_nimages_total,
            anchor=CENTER).place(x=200, y=100, width=200)
        ttk.Label(frame1, text="Today's images:").place(x=30, y=140)
        ttk.Label(
            frame1, textvariable=self.var_nimages_today,
            anchor=CENTER).place(x=200, y=140, width=200)

        ttk.LabelFrame(
            frame1, text="Clip area").place(x=10, y=190, width=435, height=220)
        lb_areas = self.lb_areas = tk.Listbox(
            frame1, listvariable=self.var_listitems)
        lb_areas.place(x=30, y=230, height=158, width=205)
        scrollbar = ttk.Scrollbar(frame1, orient=VERTICAL, command=lb_areas.yview)
        lb_areas['yscrollcommand'] = scrollbar.set
        scrollbar.place(x=235, y=230, height=158)
        ttk.Button(
            frame1, text="+",
            command=self._on_plus_clicked).place(x=275, y=230, width=70)
        ttk.Button(
            frame1, text="−",
            command=self._on_minus_clicked).place(x=355, y=230, width=70)
        ttk.Button(
            frame1, text="Edit",
            command=self._on_edit_clicked).place(x=275, y=280, width=150)
        ttk.Button(
            frame1, text="Set", style='warning.TButton',
            command=self._on_set_clicked).place(x=275, y=350, width=150)
        lb_areas.bind('<<ListboxSelect>>', self._on_area_selected)

        frame2 = self.frame2 = ttk.Frame(self)
        frame2.pack(fill=BOTH, expand=True)
        clipframe = self.clipframe = ClipFrame(
            frame2, parent=self, env=self.env, clipper=self.clipper,
            counter=self.counter)
        clipframe.pack(fill=BOTH, expand=True)
        self.pack(fill=BOTH, expand=True)

    def _init_vars(self) -> None:
        self.var_clipmode.set(2)

    def _on_folder_clicked(self) -> None:
        folder = filedialog.askdirectory(title="Open folder")
        if not folder:
            return
        self._reset_folder_info(folder)

    def _on_area_selected(self, event: tk.Event) -> None:
        name = self._get_one_lbselection()
        if name is None:
            return  # EditのSpinboxを変えるとname=Noneで呼び出されるため
        rect = self.areadb.get(name)
        self._switch_preview(name, rect)

    def _on_plus_clicked(self) -> None:
        self.xparentwindow.hide()
        EditDialog(parent=self, areadb=self.areadb)

    def _on_minus_clicked(self) -> None:
        name = self._get_one_lbselection()
        if name is None:
            return
        if not messagebox.askyesno(
            "Delete Item",
            "Are you sure to delete this item?"
            "\n(The operation cannot be undone.)"):
            return

        self.areadb.delete(name)
        self.areadb.save()
        self.update_listitems()
        self.xparentwindow.hide()

        if self.clipframe.is_activated_byname(name):
            self.clipframe._init_vars()
            self.clipframe.block_widgets()

    def _on_edit_clicked(self) -> None:
        name = self._get_one_lbselection()
        if name is None:
            return
        self.xparentwindow.hide()
        EditDialog(parent=self, areadb=self.areadb, name=name)

    def _on_set_clicked(self) -> None:
        name = self._get_one_lbselection()
        if name is None:
            return
        rect = self.areadb.get(name)
        self.clipframe.register_cliparea(name, rect)
        self.clipframe.release_widgets()

    def _reset_folder_info(self, folder: str) -> None:
        self.var_folder.set(shorten(folder, maxlen=4))
        self.counter.set_dir(folder)
        self.counter.initialize_count()

    def _reset_clip_areas(self, keys: list[str]) -> None:
        self.var_listitems.set(keys)

    def _switch_preview(self, name: str, rect: Rectangle) -> None:
        if name != self.prevname:
            self.xparentwindow.hide()
            self.xparentwindow.resize(**asdict(rect))
            self.root.after(20, self.xparentwindow.preview)
            self.prevname = name
        else:
            self.xparentwindow.hide()
            self.prevname = None

    def _select_lbitem(self, name: str) -> None:
        idx = self.areadb.namelist.index(name)
        self.lb_areas.select_set(idx)
        self.lb_areas.see(idx)

    def _unselect_lbitem(self) -> None:
        idx = self.lb_areas.curselection()
        if len(idx):
            self.lb_areas.select_clear(idx[0])

    def _get_one_lbselection(self) -> str | None:
        idx = self.lb_areas.curselection()
        if idx == ():
            return None
        if len(idx) > 1:
            idx = idx[-1]
        return self.lb_areas.get(idx)


class ClipFrame(ttk.Frame):

    def __init__(
            self, root: ttk.Frame, parent: ExtractTab, env: Environment,
            clipper: Clipper, counter: ImageCounter) -> None:
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
            self, text="📸", style='warning.TButton',
            command=self._on_camera_clicked).place(x=10, y=10, width=60)
        ttk.Label(
            self, text="[                   ]",
            anchor=CENTER).place(x=80, y=15, width=130)
        ttk.Label(
            self, textvariable=self.var_areaname,
            anchor=CENTER).place(x=90, y=15, width=110)
        ttk.Radiobutton(
            self, text="Manual", value=1, variable=self.var_clipmode,
            command=self._on_manual_clicked).place(x=225, y=18)
        ttk.Radiobutton(
            self, text="Auto", value=2, variable=self.var_clipmode,
            style='danger.TRadiobutton',
            command=self._on_auto_clicked).place(x=320, y=18)
        fold_button = self.fold_button = ttk.Button(
            self, text="▲", style='secondary.Outline.TButton',
            command=self._on_fold_clicked)
        fold_button.place(x=400, y=10, width=45)

    def _init_vars(self) -> None:
        self.var_clipmode.set(1)
        self.var_areaname.set("------")

    def _on_camera_clicked(self) -> None:
        if self.clipper.area is None:
            return
        self._normal_save()

    def _on_fold_clicked(self) -> None:
        self.parent.shrink()
        self.fold_button['text'] = "▼"
        self.fold_button['command'] = self._on_unfold_clicked
        self.parent.parent.note.place_configure(height=100)

    def _on_unfold_clicked(self) -> None:
        self.parent.extend()
        self.fold_button['text'] = "▲"
        self.fold_button['command'] = self._on_fold_clicked
        self.parent.parent.note.place_configure(height=520)

    def _on_manual_clicked(self) -> None:
        if self.thread_alive:
            self._end_autoclip()
            messagebox.showinfo("Autoclip", "Autoclip stopped.")
            self.parent.release_widgets()

    def _on_auto_clicked(self) -> None:
        if messagebox.askyesno(
            "Autoclip", "Do you want to enable Autoclip?"):
            self.parent.block_widgets()
            self.root.after(500, self._start_autoclip)  # messageboxをキャプチャしないように
        else:
            self.var_clipmode.set(1)

    def _start_autoclip(self) -> None:
        def _autoclip():
            while self.thread_alive:
                self._noduplicate_save()
                sleep(self.env.auto_clip_interval)

        self.thread_alive = True
        thread = self.thread = Thread(target=_autoclip)
        thread.start()

    def _end_autoclip(self) -> None:
        if self.thread is not None:
            self.thread_alive = False
            self.thread.join()
            self.thread = None

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
            self.root.iconbitmap(ICONFILE)
        except FileNotFoundError:
            pass
        self.root.title("Edit")
        self.root.geometry("460x250")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.protocol('WM_DELETE_WINDOW', self._on_cancel)
        self.root.grab_set()

    def _create_widgets(self) -> None:
        ttk.Label(self, text="Area name: ").place(x=10, y=20)
        ttk.Entry(
            self,
            textvariable=self.name).place(x=130, y=20, width=320, height=37)
        ttk.LabelFrame(self, text="Area").place(
            x=10, y=60, width=440, height=130)
        ttk.Button(
            self, text="Direct\nDraw",
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
            style='secondary.TButton').place(x=40, y=200, width=160)
        ttk.Button(
            self, text="Cancel", command=self._on_cancel,
            style='secondary.Outline.TButton').place(x=260, y=200, width=160)
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
        self.root.attributes('-alpha', 0.1)
        x, y, w, h = get_expanded_screen_info()
        self.root.geometry(f'{w}x{h}+{x}+{y}')
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        self.minx, self.miny = x, y

    def _create_widgets(self) -> None:
        canvas = self.canvas = tk.Canvas(self, bg='cyan', highlightthickness=0)
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
        self.root.attributes('-alpha', 0.3)
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        TransparentWindow.roots.append(self.root)

    def _create_widgets(self) -> None:
        frame = self.markframe = tk.Frame(self, bg='white')
        size_v = 30
        size_h = int(size_v * 1.6)
        size_c = int(size_v * 0.4)
        tk.Label(
            frame, text='◀◁', font=('', size_h, 'bold'),
            fg='black', bg='white').pack(side=LEFT, fill=Y)
        tk.Label(
            frame, text='▷▶', font=('', size_h, 'bold'),
            fg='black', bg='white').pack(side=RIGHT, fill=Y)
        tk.Label(
            frame, text='▲\n△', font=('', size_v),
            fg='black', bg='white').pack(side=TOP)
        tk.Label(
            frame, text='▽\n▼', font=('', size_v),
            fg='black', bg='white').pack(side=BOTTOM)
        tk.Label(
            frame, text='＋', font=('', size_c),
            fg='black', bg='white').pack(expand=True)
        self.pack(fill=BOTH, expand=True)


class MergeTab(ttk.Frame):

    def __init__(
        self, root: tk.Tk, parent: Application, env: Environment) -> None:
        super().__init__(root)
        self.root = root
        self.image_paths = None
        self.pdf_path = None
        self.var_nimages_total = tk.IntVar()
        self.var_imagename_from = tk.StringVar()
        self.var_imagename_to = tk.StringVar()
        self.var_pdfpath = tk.StringVar()
        self.var_pwd1 = tk.StringVar()
        self.var_pwd2 = tk.StringVar()
        self.converter = PdfConverter(env)
        self.passlock = PassLock(env)

        self._create_widgets()
        self._init_vars_conversion()
        self._init_vars_protection()

    def block_widgets(self) -> None:
        for widget in self.winfo_children():
            try:
                widget['state'] = DISABLED
            except tk.TclError:
                pass

    def release_widgets(self) -> None:
        for widget in self.winfo_children():
            try:
                if widget.winfo_name() in ('!entry', '!entry2', '!entry3'):
                    widget['state'] = 'readonly'
                else:
                    widget['state'] = NORMAL
            except tk.TclError:
                pass

    def _create_widgets(self) -> None:
        ttk.LabelFrame(
            self,
            text="PDF conversion").place(x=10, y=10, width=435, height=130)
        ttk.Button(
            self, text="📁", style='secondary.Outline.TButton',
            command=self._on_imagefolder_clicked).place(x=30, y=50, width=45)
        ttk.Entry(
            self, textvariable=self.var_imagename_from,
            state='readonly').place(x=80, y=50, width=160, height=37)
        ttk.Label(self, text="–").place(x=246, y=52)
        ttk.Entry(
            self, textvariable=self.var_imagename_to,
            state='readonly').place(x=267, y=50, width=160, height=37)
        ttk.Label(self, text="Total images:").place(x=30, y=100)
        ttk.Label(
            self, textvariable=self.var_nimages_total,
            anchor=CENTER).place(x=200, y=100, width=200)
        ttk.Button(
            self, text="Convert",
            command=self._on_convert_clicked).place(x=150, y=155, width=160)
        ttk.LabelFrame(
            self, text="Password protection").place(
                x=10, y=220, width=435, height=200)
        ttk.Button(
            self, text="📁", style='secondary.Outline.TButton',
            command=self._on_pdffolder_clicked).place(x=30, y=260, width=45)
        ttk.Entry(
            self, textvariable=self.var_pdfpath,
            state='readonly').place(x=80, y=260, width=345, height=37)
        ttk.Label(self, text="Password:").place(x=30, y=320)
        ent_pwd1 = self.ent_pwd1 = ttk.Entry(self, textvariable=self.var_pwd1)
        ent_pwd1.place(x=145, y=315, width=280, height=37)
        ttk.Label(self, text="Again:").place(x=30, y=370)
        ent_pwd2 = self.ent_pwd2 = ttk.Entry(
            self, show="●", textvariable=self.var_pwd2)
        ent_pwd2.place(x=145, y=365, width=280, height=37)
        btn_lock = self.btn_lock = ttk.Button(self)
        btn_lock.place(x=150, y=435, width=160)
        self.pack(fill=BOTH, expand=True)

    def _init_vars_conversion(self) -> None:
        self.var_imagename_from.set("")
        self.var_imagename_to.set("")
        self.var_nimages_total.set(0)
        self.image_paths = None

    def _init_vars_protection(self) -> None:
        self.var_pdfpath.set("")
        self.var_pwd1.set("")
        self.var_pwd2.set("")
        self.ent_pwd1['show'] = "●"
        self.btn_lock['text'] = "Lock/Unlock"
        self.btn_lock['command'] = lambda: None
        self.pdf_path = None

    def _on_imagefolder_clicked(self) -> None:
        images = filedialog.askopenfilenames(
            title="Select Images", filetypes=[('png', '*.png')])
        if not images:
            return

        self.var_imagename_from.set(noext_basename(images[0]))
        if len(images) > 1:
            self.var_imagename_to.set(noext_basename(images[-1]))
        else:
            self.var_imagename_to.set("")
        self.var_nimages_total.set(len(images))
        self.image_paths = images

    def _on_convert_clicked(self) -> None:
        if self.image_paths is None:
            return
        savepath = filedialog.asksaveasfilename(
            title="Save as", filetypes=[('pdf', '*.pdf')])
        if not savepath:
            return
        savepath = append_ext(savepath, '.pdf')

        self.block_widgets()
        with ProgressWindow(
            self, "PDF Conversion", "Packing images into a pdf...") as pb:
            pb.during(self.converter.save_as_pdf, self.image_paths, savepath)
            pb.after(self._init_vars_conversion)
            pb.final(self.release_widgets)

    def _on_pdffolder_clicked(self) -> None:
        pdf_path = filedialog.askopenfilename(
            title="Select PDF", filetypes=[('pdf', '*.pdf')])
        if not pdf_path:
            return

        self._init_vars_protection()
        self.pdf_path = pdf_path
        self.var_pdfpath.set(shorten(pdf_path, maxlen=2))
        if self.passlock.check_encryption(pdf_path):
            self.ent_pwd1['show'] = ""
            self.ent_pwd2.place_forget()
            self.btn_lock['text'] = "Unlock"
            self.btn_lock['command'] = self._unlock
        else:
            self.ent_pwd1['show'] = "●"
            self.ent_pwd2.place(x=145, y=365, width=280, height=37)
            self.btn_lock['text'] = "Lock"
            self.btn_lock['command'] = self._lock

    def _lock(self) -> None:
        pdfpath = self.pdf_path
        if pdfpath is None:
            return
        pwd1, pwd2 = self.var_pwd1.get(), self.var_pwd2.get()
        if not self._verify(pwd1, pwd2):
            return
        savepath = filedialog.asksaveasfilename(
            title="Save as", filetypes=[('pdf', '*.pdf')])
        if not savepath:
            return
        savepath = append_ext(savepath, '.pdf')

        self.block_widgets()
        with ProgressWindow(
            self, "Password Protection", "Trying to encrypt...") as pb:
            pb.during(self.passlock.encrypt, pdfpath, savepath, pwd1)
            pb.after(self._init_vars_protection)
            pb.final(self.release_widgets)

    def _unlock(self) -> None:
        pdfpath = self.pdf_path
        if pdfpath is None:
            return
        pwd1 = self.var_pwd1.get()
        if not self._verify(pwd1):
            return

        self.block_widgets()
        with ProgressWindow(
            self, "Password Protection", "Trying to decrypt...") as pb:
            pb.during(self.passlock.decrypt, pdfpath, pdfpath, pwd1)
            pb.after(self._init_vars_protection)
            pb.final(self.release_widgets)

    def _verify(self, pwd1: str, pwd2: str = None) -> bool:
        if pwd1 == "":
            messagebox.showerror(
                "Invalid input", "Enter a password in first entry box.")
            return False
        elif pwd2 is not None and pwd1 != pwd2:
            messagebox.showerror(
                "Invalid input",
                "Enter the same password in the second entry box.")
            return False
        return True


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


class SettingsWindow(ttk.Frame):

    def __init__(self, parent: Application, env: Environment) -> None:
        root = self.root = tk.Toplevel(parent)
        super().__init__(root)
        self.parent = parent
        self.env = env
        self.var_theme = tk.StringVar()
        self.var_area_file = tk.StringVar()
        self.var_default_save_folder = tk.StringVar()
        self.var_pixel_difference_threshold = tk.IntVar()
        self.var_image_duplication_check_steps = tk.IntVar()
        self.var_auto_clip_interval = tk.DoubleVar()
        self.var_compress_before_pdf_conversion = tk.BooleanVar()
        self.var_compression_ratio = tk.IntVar()
        self.var_resize_before_pdf_conversion = tk.BooleanVar()
        self.var_resized_height = tk.IntVar()
        self.var_zip_converted_images = tk.BooleanVar()
        self.var_password_security_level = tk.IntVar()

        self._setup_root()
        self._init_vars()
        self._create_widgets()

    def _setup_root(self) -> None:
        try:
            self.root.iconbitmap(ICONFILE)
        except FileNotFoundError:
            pass
        self.root.title("Environment Settings")
        self.root.geometry('460x640')
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.protocol('WM_DELETE_WINDOW', self._on_cancel)

    def _create_widgets(self) -> None:
        ttk.Label(self, text="Theme").place(x=20, y=20)
        cbb_theme = ttk.Combobox(
            self, textvariable=self.var_theme, values=[
                'cosmo', 'flatly', 'journal', 'literal', 'lumen', 'minty',
                'pulse', 'sandstone', 'united', 'yeti', 'cyborg', 'darkly',
                'solar', 'superhero', 'alt', 'clam', 'classic', 'default',
                'vista', 'winnative', 'xpnative'])
        cbb_theme.place(x=320, y=20, width=120)
        ttk.Label(self, text="Area file").place(x=20, y=60)
        ttk.Entry(
            self, textvariable=self.var_area_file).place(
                x=20, y=90, width=420, height=37)
        ttk.Label(self, text="Default save folder").place(x=20, y=140)
        ttk.Entry(
            self, textvariable=self.var_default_save_folder).place(
                x=20, y=170, width=420, height=37)
        ttk.Label(self, text="Pixel difference threshold").place(x=20, y=220)
        ttk.Spinbox(
            self, textvariable=self.var_pixel_difference_threshold,
            from_=0, to=999999, increment=1000).place(x=320, y=220, width=120)
        ttk.Label(
            self, text="Image duplication check steps").place(x=20, y=260)
        ttk.Spinbox(
            self, textvariable=self.var_image_duplication_check_steps,
            from_=0, to=20, increment=1).place(x=320, y=260, width=120)
        ttk.Label(self, text="Auto clip interval").place(x=20, y=300)
        ttk.Spinbox(
            self, textvariable=self.var_auto_clip_interval,
            from_=0.5, to=10, increment=0.1).place(x=320, y=300, width=120)
        ttk.Label(
            self, text="Compress before pdf conversion").place(x=20, y=340)
        ttk.Checkbutton(
            self, variable=self.var_compress_before_pdf_conversion,
            command=self._on_enable_comp).place(x=375, y=345)
        ttk.Label(self, text="    - Compression ratio").place(x=20, y=380)
        spb_ratio = self.spb_ratio = ttk.Spinbox(
            self, textvariable=self.var_compression_ratio, from_=60, to=90)
        spb_ratio.place(x=320, y=380, width=120)
        ttk.Label(self, text="Resize before pdf conversion").place(x=20, y=420)
        ttk.Checkbutton(
            self, variable=self.var_resize_before_pdf_conversion,
            command=self._on_enable_resize).place(x=375, y=425)
        ttk.Label(self, text="    - Resized height").place(x=20, y=460)
        spb_height = self.spb_height = ttk.Spinbox(
            self, textvariable=self.var_resized_height, from_=10, to=9999)
        spb_height.place(x=320, y=460, width=120)
        ttk.Label(self, text="Zip converted images").place(x=20, y=500)
        ttk.Checkbutton(
            self, variable=self.var_zip_converted_images).place(x=375, y=505)
        ttk.Label(self, text="Password security level").place(x=20, y=540)
        ttk.Spinbox(
            self, textvariable=self.var_password_security_level,
            from_=1, to=3).place(x=320, y=540, width=120)
        ttk.Button(
            self, text="OK", command=self._on_ok,
            style='secondary.TButton').place(x=40, y=590, width=160)
        ttk.Button(
            self, text="Cancel", command=self._on_cancel,
            style='secondary.Outline.TButton').place(x=260, y=590, width=160)
        self.pack(fill=BOTH, expand=True)
        cbb_theme.bind(
            '<<ComboboxSelected>>',
            lambda event: self._change_theme(self.var_theme.get()))
        self._change_theme(self.var_theme.get())
        self._on_enable_comp()
        self._on_enable_resize()

    def _init_vars(self) -> None:
        env = self.env
        for key, val in asdict(env).items():
            var = getattr(self, 'var_'+key)
            var.set(val)

    def _on_enable_comp(self) -> None:
        if not self.var_compress_before_pdf_conversion.get():
            self.spb_ratio['state'] = DISABLED
        else:
            self.spb_ratio['state'] = NORMAL

    def _on_enable_resize(self) -> None:
        if not self.var_resize_before_pdf_conversion.get():
            self.spb_height['state'] = DISABLED
        else:
            self.spb_height['state'] = NORMAL

    def _on_ok(self) -> None:
        env = self.env
        for key in asdict(env).keys():
            var = getattr(self, 'var_'+key)
            setattr(env, key, var.get())
        env.save()
        self.env = env
        self.root.destroy()

    def _on_cancel(self) -> None:
        env = self.env
        for key, val in asdict(env).items():
            var = getattr(self, 'var_'+key)
            if val != var.get():
                if not messagebox.askyesno(
                    "Settings", "Do you want to leave? \n(Edits are not saved.)"):
                    return
                break
        self._change_theme(self.env.theme)
        self.root.destroy()

    def _vars(self) -> list[str]:
        return list(filter(lambda attr: attr.startswith('var'), dir(self)))

    def _change_theme(self, theme: str) -> None:
        Style().theme_use(theme)


if __name__ == '__main__':
    set_high_resolution()
    root = tk.Tk()
    Application(root)
    root.mainloop()
