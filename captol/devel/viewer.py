from glob import glob
from importlib import reload, import_module
import os
from os.path import dirname, basename, join

import tkinter as tk
from tkinter import BOTH
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


def source_pyfiles(*dirs):
    files = []
    for dir_ in dirs:
        files += glob(join(dir_, '*.py'))
    return list(map(lambda fp: basename(fp), files))


CURDIR = dirname(__file__)
PARDIR = join(CURDIR, '..\\')
FILES = source_pyfiles(
    join(PARDIR, 'frontend'),
    join(PARDIR, 'backend'),
    PARDIR, CURDIR)


def windows_high_resolution():
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(True)


class TkHandler(FileSystemEventHandler):
    def __init__(self, callback, filenames):
        super().__init__()
        self.callback = callback
        self.filenames = filenames
        self.old = 0

    def on_modified(self, event):
        fullpath = event.src_path
        if basename(fullpath) in self.filenames:
            statbuf = os.stat(fullpath)
            self.new = statbuf.st_mtime
            if (self.new - self.old) > 0.5:
                self.callback()
            self.old = self.new


class TkViewer(tk.Frame):

    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.widget = None

    def run(self):
        observer = Observer()
        observer.schedule(TkHandler(self.update, FILES), PARDIR, recursive=True)
        observer.start()
        self.update()

    def update(self):
        self.clear()
        try:
            self.load()
            self.show_ui()
        except Exception as e:
            from traceback import TracebackException
            print(''.join(TracebackException.from_exception(e).format()))
            self.show_message(e)

    def clear(self):
        if self.widget is not None:
            self.widget.destroy()
            self.pack_forget()

    def load(self):
        try:
            self.ui = reload(self.ui)
        except AttributeError:
            self.ui = import_module('captol.frontend.ui')

    def show_ui(self):
        self.widget = self.ui.Application(self.root)
        print('GUI refreshed')

    def show_message(self, e):
        widget = self.widget = tk.Message(self, text=str(e))
        widget.bind(
            "<Configure>",
            lambda event: event.widget.config(width=self.root.winfo_width()))
        widget.pack(fill=BOTH, expand=True)
        self.pack(fill=BOTH, expand=True)


def run() -> None:
    print('Running in developer mode')
    try:
        windows_high_resolution()
    except:
        pass

    root = tk.Tk()
    root.attributes('-topmost', True)
    TkViewer(root).run()
    root.mainloop()
