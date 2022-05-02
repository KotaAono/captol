from __future__ import annotations
from dataclasses import asdict
import tkinter as tk
from tkinter import BOTH, DISABLED, NORMAL, CENTER, VERTICAL
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import ttkbootstrap as ttk

from captol.frontend.clipframe import ClipFrame, EditDialog
from captol.utils.path import shorten
from captol.frontend.subframe import TransparentWindow
from captol.backend.extraction import Clipper, ImageCounter
from captol.backend.data import AreaDB

if TYPE_CHECKING:
    from captol.frontend.mainframe import Application
    from captol.backend.data import Rectangle, Environment



class ExtractTab(ttk.Frame):

    def __init__(
        self, root: ttk.Notebook, parent: Application, env: Environment
    ) -> None:
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
        self.parent.resize('460x100')

    def extend(self) -> None:
        self.frame2.pack_forget()
        self.frame1.pack(fill=BOTH, expand=True)
        self.frame2.pack(fill=BOTH, expand=True, pady=5)
        self.parent.enable_mergetab()
        self.parent.resize('460x510')

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
            text="Save folder info").place(x=10, y=10, width=435, height=170)
        ttk.Button(
            frame1, text="📁", bootstyle='secondary-outline-button',
            command=self._on_folder_clicked).place(x=30, y=50, width=45)
        ttk.Entry(
            frame1, textvariable=self.var_folder,
            state='readonly').place(x=80, y=50, width=345)
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
        lb_areas.place(x=30, y=230, height=160, width=205)
        scrollbar = ttk.Scrollbar(frame1, orient=VERTICAL, command=lb_areas.yview)
        lb_areas['yscrollcommand'] = scrollbar.set
        scrollbar.place(x=235, y=230, height=160)
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
            frame1, text="Set", bootstyle='warning-button',
            command=self._on_set_clicked).place(x=275, y=350, width=150)
        lb_areas.bind('<<ListboxSelect>>', self._on_area_selected)

        frame2 = self.frame2 = ttk.Frame(self)
        frame2.pack(fill=BOTH, expand=True, pady=5)
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
