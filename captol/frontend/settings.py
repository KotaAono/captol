from __future__ import annotations
from dataclasses import asdict
import tkinter as tk
from tkinter import BOTH, DISABLED, NORMAL
from tkinter import messagebox
from typing import TYPE_CHECKING

import ttkbootstrap as ttk

from captol.utils.const import ICON_FILE
if TYPE_CHECKING:
    from captol.frontend.mainframe import Application
    from captol.backend.data import Environment


class SettingsWindow(ttk.Frame):

    def __init__(self, parent: Application, env: Environment) -> None:
        root = self.root = ttk.Toplevel(parent)
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
            self.root.iconbitmap(ICON_FILE)
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
            self, textvariable=self.var_theme,
            values=self.parent.style.theme_names())
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
            bootstyle='primary-button').place(x=40, y=590, width=160)
        ttk.Button(
            self, text="Cancel", command=self._on_cancel,
            bootstyle='primary-outline-button').place(x=260, y=590, width=160)
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

    def _change_theme(self, theme: str) -> None:
        self.parent.style.theme_use(theme)
