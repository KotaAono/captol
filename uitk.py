from __future__ import annotations
from ctypes import windll
from dataclasses import asdict
from os.path import basename, splitext, isfile
from threading import Thread
from time import sleep
import tkinter as tk
from tkinter import BOTH, DISABLED, NORMAL, CENTER, LEFT, RIGHT, TOP, BOTTOM, Y
from tkinter import ttk
from tkinter import filedialog, messagebox
from typing import Any

from ttkbootstrap import Style

from memory import AreaDB, Rectangle, Environment
from extraction import Clipper, ImageCounter, ImageBuffer
from storage import PdfConverter, PassLock


ICONFILE = 'favicon.ico'


def high_resolution() -> None:
    windll.shcore.SetProcessDpiAwareness(True)    


def noext_basename(path: str) -> str:
    return splitext(basename(path))


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


class Application(ttk.Frame):

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root)
        self.root = root
        self.settingswindow = None
        self.env = Environment.load()

        self._setup_root()
        self._create_widgets()

    def resize(self, geometry: str) -> None:
        self.root.geometry(geometry)

    def enable_mergetab(self) -> None:
        self.note.tab(1, state=NORMAL)

    def disable_mergetab(self) -> None:
        self.note.tab(1, state=DISABLED)

    def _setup_root(self) -> None:
        self.root.iconbitmap(ICONFILE)
        self.root.title("Captol dev")
        self.root.attributes('-topmost', True)
        self.root.geometry("460x530-0+0")
        self.root.resizable(False, False)
        self.root = Style("darkly").master

    def _create_widgets(self) -> None:
        note = self.note = ttk.Notebook(self)
        note.root = self
        note.place(x=0, y=10, relwidth=1, relheight=1)
        note.add(ExtractTab(
            note, parent=self, env=self.env), text="1. Extract")
        note.add(StoreFrame(
            note, parent=self, env=self.env), text=" 2. Merge ")
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
            self, root: tk.Tk, parent: Application, env: Environment) -> None:
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
        self._reset_folder_info(env.default_folder)
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
                widget['state'] = NORMAL
            except tk.TclError:
                pass
    
    def update_listitems(self, activate_name : str = None) -> None:
        self._reset_clip_areas(self.areadb.namelist)
        if activate_name is not None:
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
            state='readonly').place(x=80, y=52, width=345)
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
        lb_areas.place(x=30, y=230, height=160)
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
            frame1, text="Launch", style='warning.TButton',
            command=self._on_launch_clicked).place(x=275, y=350, width=150)
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

    def _on_area_selected(self, event: Any) -> None:
        name = self._get_one_lbselection()
        rect = self.areadb.get(name)
        self._switch_preview(name, rect)

    def _on_plus_clicked(self) -> None:
        self.xparentwindow.hide()
        EditDialog(parent=self, areadb=self.areadb)

    def _on_minus_clicked(self) -> None:
        name = self._get_one_lbselection()
        if name is None:
            return
        if messagebox.askyesno(
            "Delete Item",
            "Are you sure to delete this item?"
            "\n(The operation cannot be undone.)"):
            return
            
        self.areadb.delete(name)
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
        
    def _on_launch_clicked(self) -> None:
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
    
    def _reset_clip_areas(self, keys: list) -> None:
        self.var_listitems.set(keys)

    def _switch_preview(self, name: str, rect: Rectangle) -> None:
        if name != self.prevname:
            self.xparentwindow.resize(**asdict(rect))
            self.xparentwindow.preview()
            self.prevname = name
        else:
            self.xparentwindow.hide()
            self.prevname = None

    def _select_lbitem(self, name: str) -> None:
        idx = self.areadb.namelist.index(name)
        self.lb_areas.select_set(idx)
        self.lb_areas.see(idx)
    
    def _get_one_lbselection(self) -> str | None:
        idx = self.lb_areas.curselection()
        if idx == ():
            return None
        if len(idx) > 1:
            idx = idx[-1]
        return self.lb_areas.get(idx)


class ClipFrame(ttk.Frame):

    def __init__(
            self, root: tk.Tk, parent: ExtractTab, env: Environment,
            clipper: Clipper, counter: ImageCounter) -> None:
        super().__init__(root)
        self.parent = parent
        self.env = env
        self.clipper = clipper
        self.counter = counter
        self.thread = None
        self.thread_alive = False
        self.var_clipmode = tk.IntVar()
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

    def _on_unfold_clicked(self) -> None:
        self.parent.extend()
        self.fold_button['text'] = "▲"
        self.fold_button['command'] = self._on_fold_clicked

    def _on_manual_clicked(self) -> None:
        if self.thread_alive:
            self._end_autoclip()
            messagebox.showinfo("Autoclip", "Autoclip stopped.")
            self.parent.release_widgets()

    def _on_auto_clicked(self) -> None:
        if messagebox.askyesno(
            "Autoclip", "Do you want to enable Autoclip?"):
            self.parent.block_widgets()
            self._start_autoclip()
        else:
            self.var_clipmode.set(1)

    def _start_autoclip(self) -> None:
        def _autoclip():
            while self.thread_alive:
                if self.env.enable_active_image_saver:
                    self._active_save()
                else:
                    self._nodup_save()
                sleep(self.env.autoclip_interval)

        self.thread_alive = True
        thread = self.thread = Thread(target=_autoclip)
        thread.start()
    
    def _end_autoclip(self) -> None:
        if self.thread is not None:
            self.thread_alive = False
            self.thread.join()
            self.thread = None

    def _normal_save(self) -> None:
        self.xparentwindow.hide_all()
        image = self.clipper.clip()
        self.imbuffer.hold(image)
        name = self.counter.next_savepath()
        self.imbuffer.save(name)
        self.xparentwindow.flash()
        self.counter.up(1)

    def _nodup_save(self) -> None:
        self.xparentwindow.hide_all()
        image = self.clipper.clip()
        self.imbuffer.hold(image)

        if self.imbuffer.compare_similarity(past_step=1):
            self.imbuffer.release()
        else:
            name = self.counter.next_savepath()
            self.imbuffer.save(name)
            self.xparentwindow.flash()
            self.counter.up(1)

    def _active_save(self) -> None:
        self.xparentwindow.hide_all()
        image = self.clipper.clip()
        self.imbuffer.hold(image)

        if self.imbuffer.compare_similarity(past_step=1):
            self.imbuffer.release()
        elif self.imbuffer.compare_similarity(past_step=2):
            self.imbuffer.delete(past_step=2)
            self.imbuffer.delete(past_step=1)
            name = self.counter.next_savepath()
            self.imbuffer.save(name)
            self.xparentwindow.flash()
            self.counter.down(1)
        else:
            name = self.counter.next_savepath()
            self.imbuffer.save(name)
            self.xparentwindow.flash()
            self.counter.up(1)


class EditDialog(ttk.Frame):

    def __init__(
            self, parent: ExtractTab, areadb: AreaDB,
            name: str = None) -> None:
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
        self.root.iconbitmap(ICONFILE)
        self.root.title("Edit")
        self.root.geometry("460x250")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.protocol('WM_DELETE_WINDOW', self._on_cancel)
        self.root.grab_set()

    def _create_widgets(self) -> None:
        ttk.Label(self, text="Area name: ").place(x=10, y=20)
        ttk.Entry(self, textvariable=self.name).place(x=130, y=20, width=320)
        ttk.LabelFrame(self, text="Area").place(
            x=10, y=60, width=440, height=130)
        ttk.Button(
            self, text="Direct\nDraw",
            command=self._on_direct_draw).place(x=30, y=95, width=90, height=80)
        ttk.Label(self, text="x:").place(x=150, y=95)
        ttk.Spinbox(self, textvariable=self.x, from_=0, to=9999).place(
            x=180, y=95, width=80)
        ttk.Label(self, text="width:").place(x=280, y=95)
        ttk.Spinbox(self, textvariable=self.w, from_=0, to=9999).place(
            x=350, y=95, width=80)
        ttk.Label(self, text="y:").place(x=150, y=140)
        ttk.Spinbox(self, textvariable=self.y, from_=0, to=9999).place(
            x=180, y=140, width=80)
        ttk.Label(self, text="height:").place(x=280, y=140)
        ttk.Spinbox(self, textvariable=self.h, from_=0, to=9999).place(
            x=350, y=140, width=80)
        ttk.Button(
            self, text="OK", command=self._on_ok,
            style='secondary.TButton').place(x=40, y=200, width=160)
        ttk.Button(
            self, text="Cancel", command=self._on_cancel,
            style='secondary.Outline.TButton').place(x=260, y=200, width=160)
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

    def _on_ok(self) -> None:
        name = self.name.get()
        x, y, w, h = self.x.get(), self.y.get(), self.w.get(), self.h.get()
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
        if min(x, y, w, h) < 0:
            messagebox.showerror(
                "Invalid Input", "Minous value is not allowed.")
            return False
        return True


class Drawer(ttk.Frame):

    def __init__(
        self, parent: EditDialog, xparentwindow: TransparentWindow,
        var_x: tk.IntVar, var_y: tk.IntVar, var_w: tk.IntVar,
        var_h: tk.IntVar) -> None:
        root = self.root = tk.Toplevel(parent)
        super().__init__(root)
        self.root = root
        self.parent = parent
        self.var_x = var_x
        self.var_y = var_y
        self.var_w = var_w
        self.var_h = var_h
        self.start_x = None
        self.start_y = None
        self.xparentwindow = xparentwindow

        self._setup_root()
        self._create_widgets()  # iconifyは座標がずれる
        parent.block_widgets()

    def _setup_root(self) -> None:
        self.root.attributes('-alpha', 0.1)
        self.root.attributes('-fullscreen', True)
        self.root.resizable(False, False)
        self.root.overrideredirect(True)

    def _create_widgets(self) -> None:
        canvas = self.canvas = tk.Canvas(self, bg='cyan', highlightthickness=0)
        canvas.pack(fill=BOTH, expand=True)
        canvas.bind('<ButtonPress-1>', self._on_drag_start)
        canvas.bind('<B1-Motion>', self._on_moving)
        canvas.bind('<ButtonRelease>', self._on_drag_end)
        self.pack(fill=BOTH, expand=True)

    def _on_drag_start(self, event: Any) -> None:
        self.start_x = event.x
        self.start_y = event.y
        self.xparentwindow.resize(0, 0, 0, 0)
        self.xparentwindow.preview()

    def _on_moving(self, event: Any) -> None:
        sx, sy, cx, cy = self.start_x, self.start_y, event.x, event.y
        x, y, w, h = min(sx, cx), min(sy, cy), abs(sx-cx), abs(sy-cy)
        self.xparentwindow.resize(x, y, w, h)

    def _on_drag_end(self, event: Any) -> None:
        sx, sy, cx, cy = self.start_x, self.start_y, event.x, event.y
        self.var_x.set(min(sx, cx))
        self.var_y.set(min(sy, cy))
        self.var_w.set(abs(sx-cx))
        self.var_h.set(abs(sy-cy))
        self.parent.release_widgets()
        self.root.destroy()


class TransparentWindow(tk.Frame):
    roots: list[tk.Tk] = list()

    def __init__(self, parent: Any) -> None:
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


class StoreFrame(ttk.Frame):

    def __init__(
        self, root: tk.Tk, parent: Application, env: Environment) -> None:
        super().__init__(root)
        self.image_paths = None
        self.pdf_path = None
        self.var_nimages_total = tk.IntVar()
        self.var_imagename_from = tk.StringVar()
        self.var_imagename_to = tk.StringVar()
        self.var_pdfpath = tk.StringVar()
        # open ...\Univaイベント\JR東海pw.pdf: No such file or directory
        self.var_pwd1 = tk.StringVar()
        self.var_pwd2 = tk.StringVar()
        self.converter = PdfConverter(env)
        self.passlock = PassLock(env)

        self._create_widgets()
        self._init_vars_conversion()
        self._init_vars_protection()

    def _create_widgets(self) -> None:
        ttk.LabelFrame(
            self,
            text="PDF conversion").place(x=10, y=10, width=435, height=130)
        ttk.Button(
            self, text="📁", style='secondary.Outline.TButton',
            command=self._on_imagefolder_clicked).place(x=30, y=50, width=45)
        ttk.Entry(
            self, textvariable=self.var_imagename_from,
            state='readonly').place(x=80, y=52, width=160)
        ttk.Label(self, text="–").place(x=246, y=52)
        ttk.Entry(
            self, textvariable=self.var_imagename_to,
            state='readonly').place(x=267, y=52, width=160)
        ttk.Label(self, text="Total images:").place(x=30, y=100)
        ttk.Label(
            self, textvariable=self.var_nimages_total,
            anchor=CENTER).place(x=200, y=100, width=200)
        ttk.Button(
            self, text="Convert",
            command=self._on_convert_clicked).place(x=150, y=150, width=160)
        ttk.LabelFrame(
            self, text="Password protection").place(
                x=10, y=220, width=435, height=200)
        ttk.Button(
            self, text="📁", style='secondary.Outline.TButton',
            command=self._on_pdffolder_clicked).place(x=30, y=260, width=45)
        ttk.Entry(
            self, textvariable=self.var_pdfpath,
            state='readonly').place(x=80, y=262, width=345)
        ttk.Label(self, text="Password:").place(x=30, y=320)
        ent_pwd1 = self.ent_pwd1 = ttk.Entry(self, textvariable=self.var_pwd1)
        ent_pwd1.place(x=145, y=317, width=280)
        ttk.Label(self, text="Again:").place(x=30, y=370)
        ent_pwd2 = self.ent_pwd2 = ttk.Entry(
            self, show="●", textvariable=self.var_pwd2)
        ent_pwd2.place(x=145, y=366, width=280)
        btn_lock = self.btn_lock = ttk.Button(self)
        btn_lock.place(x=150, y=430, width=160)
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
        self.ent_pwd1['state'] = DISABLED
        self.ent_pwd2['state'] = DISABLED
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
        if not savepath.endswith(('.pdf', '.PDF')):
            savepath += '.pdf'
        if isfile(savepath):
            if not messagebox.askyesno(
                "Save pdf",
                "A pdf file with the same name already exists."
                "\nAre you sure to overwrite it?"):
                return
        
        self.converter.save_as_pdf(self.image_paths, savepath)
        self._init_vars_conversion()

    def _on_pdffolder_clicked(self):
        pdf_path = filedialog.askopenfilename(
            title="Select PDF", filetypes=[('pdf', '*.pdf')])
        if not pdf_path:
            return

        self._init_vars_protection()
        self.pdf_path = pdf_path
        self.var_pdfpath.set(shorten(pdf_path, maxlen=2))
        self.ent_pwd1['state'] = NORMAL
        if self.passlock.check_encryption(pdf_path):
            self.ent_pwd1['show'] = ""
            self.ent_pwd2['state'] = DISABLED
            self.btn_lock['text'] = "Unlock"
            self.btn_lock['command'] = self._unlock
        else:
            self.ent_pwd1['show'] = "●"
            self.ent_pwd2['state'] = NORMAL
            self.btn_lock['text'] = "Lock"
            self.btn_lock['command'] = self._lock

    def _lock(self) -> None:
        pdfpath = self.pdf_path
        if pdfpath is None:
            return
        
        pwd1, pwd2 = self.var_pwd1.get(), self.var_pwd2.get()
        if pwd1 == "":
            messagebox.showerror(
                "Invalid input", "Enter a password in first entry box.")
            return
        if pwd1 != pwd2:
            messagebox.showerror(
                "Invalid input",
                "Enter the same password in the second entry box.")
            return
        
        savepath = filedialog.asksaveasfilename(
            title="Save as", filetypes=[('pdf', '*.pdf')])
        if not savepath:
            return
        if not savepath.endswith(('.pdf', '.PDF')):
            savepath += '.pdf'
        
        try:
            self.passlock.encrypt(pdfpath, savepath, pwd1)
            messagebox.showinfo("Lock", "Completed!")
            self._init_vars_protection()
        except Exception as e:
            messagebox.showerror("Lock", e)
    
    def _unlock(self) -> None:
        pdfpath = self.pdf_path
        if pdfpath is None:
            return
        
        pwd1 = self.var_pwd1.get()
        if pwd1 == "":
            messagebox.showerror(
                "Invalid input", "Enter a password in first entry box.")
            return

        try:
            self.passlock.decrypt(pdfpath, pdfpath, pwd1)
            messagebox.showinfo("Unlock", "Completed!")
            self._init_vars_protection()
        except Exception as e:
            messagebox.showerror("Unlock", e)
            return


class SettingsWindow(ttk.Frame):
    
    def __init__(self, parent: Application, env: Environment) -> None:
        root = self.root = tk.Toplevel(parent)
        super().__init__(root)
        self.parent = parent
        self.env = env
        self.var_default_folder = tk.StringVar()
        self.var_enable_active_image_saver = tk.BooleanVar()
        self.var_enable_pdf_compression = tk.BooleanVar()
        self.var_compression_ratio = tk.IntVar()
        self.var_password_security_level = tk.IntVar()

        self._setup_root()
        self._create_widgets()
        self._init_vars()

    def _setup_root(self) -> None:
        self.root.iconbitmap(ICONFILE)
        self.root.title("Environment Settings")
        self.root.geometry('460x320')
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)

    def _create_widgets(self) -> None:
        ttk.Label(self, text="Default folder").place(x=20, y=20)
        ttk.Entry(
            self,
            textvariable=self.var_default_folder).place(x=20, y=50, width=420)
        ttk.Label(self, text="Enable Active Image Saver").place(x=20, y=100)
        ttk.Checkbutton(
            self,
            variable=self.var_enable_active_image_saver).place(x=400, y=100)
        ttk.Label(self, text="Enable pdf compression").place(x=20, y=140)
        ttk.Checkbutton(
            self, variable=self.var_enable_pdf_compression,
            command=self._on_enable_comp).place(x=400, y=140)
        ttk.Label(self, text="Compression ratio").place(x=20, y=180)
        spb_ratio = self.spb_ratio = ttk.Spinbox(
            self, textvariable=self.var_compression_ratio, from_=60, to=90)
        spb_ratio.place(x=380, y=180, width=60)
        ttk.Label(self, text="Password security level").place(x=20, y=220)
        ttk.Spinbox(
            self, textvariable=self.var_password_security_level,
            from_=1, to=3).place(x=380, y=220, width=60)
        ttk.Button(
            self, text="OK", command=self._on_ok,
            style='secondary.TButton').place(x=40, y=270, width=160)
        ttk.Button(
            self, text="Cancel", command=self._on_cancel,
            style='secondary.Outline.TButton').place(x=260, y=270, width=160)
        self.pack(fill=BOTH, expand=True)
    
    def _init_vars(self) -> None:
        env = self.env
        self.var_default_folder.set(env.default_folder)
        self.var_enable_active_image_saver.set(env.enable_active_image_saver)
        self.var_enable_pdf_compression.set(env.enable_pdf_compression)
        self.var_compression_ratio.set(env.compression_ratio)
        self.var_password_security_level.set(env.password_security_level)

    def _on_enable_comp(self) -> None:
        if not self.var_enable_pdf_compression.get():
            self.spb_ratio['state'] = DISABLED
        else:
            self.spb_ratio['state'] = NORMAL
    
    def _on_ok(self) -> None:
        env = self.env
        env.default_folder = self.var_default_folder.get()
        env.enable_active_image_saver = \
            self.var_enable_active_image_saver.get()
        env.enable_pdf_compression = self.var_enable_pdf_compression.get()
        env.compression_ratio = self.var_compression_ratio.get()
        env.password_security_level = self.var_password_security_level.get()
        self.env = env
        env.save()
        self.root.destroy()

    def _on_cancel(self) -> None:
        if messagebox.askyesno(
            "Settings", "Do you want to leave? \n(Edits are not saved.)"):
            self.root.destroy()


if __name__ == '__main__':
    try:
        high_resolution()
    except:
        pass
    root = tk.Tk()
    Application(root)
    root.mainloop()
