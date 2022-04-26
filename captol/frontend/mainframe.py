from __future__ import annotations
import tkinter as tk
from tkinter import BOTH, DISABLED, NORMAL
from tkinter import ttk

from ttkbootstrap import Style

from captol.frontend.extracttab import ExtractTab
from captol.frontend.mergetab import MergeTab
from captol.frontend.settings import SettingsWindow
from captol.utils.const import ICON_FILE
from captol.backend.data import Environment


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
            self.root.iconbitmap(ICON_FILE)
        except FileNotFoundError:
            pass
        self.root.title("Captol")
        self.root.attributes('-topmost', True)
        self.root.geometry("460x507-0+10")
        self.root.resizable(False, False)
        self.root = Style(self.env.theme).master

    def _create_widgets(self) -> None:
        note = self.note = ttk.Notebook(self)
        note.root = self
        note.place(x=0, y=4, relwidth=1, height=527)
        note.add(ExtractTab(
            note, parent=self, env=self.env), text="1. Extract")
        note.add(MergeTab(
            note, parent=self, env=self.env), text="2. Merge  ")
        ttk.Button(
            self, text="Settings", style='secondary.Outline.TButton',
            command=self._on_settings_clicked).place(x=360, y=0, width=95)
        self.pack(fill=BOTH, expand=True)

    def _on_settings_clicked(self) -> None:
        if not self._has_opened_settingswindow():
            self.settingswindow = SettingsWindow(parent=self, env=self.env)

    def _has_opened_settingswindow(self) -> bool:
        return self.settingswindow is not None and \
               self.settingswindow.root.winfo_exists()
