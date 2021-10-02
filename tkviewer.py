from importlib import reload, import_module
from os.path import dirname, basename, splitext
from sys import argv

import tkinter as tk
from tkinter import BOTH
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


DIR = dirname(argv[1])
FILE = basename(argv[1])


def windows_high_resolution():
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(True)


class TkHandler(FileSystemEventHandler):
    def __init__(self, callback, filename):
        super().__init__()
        self.callback = callback
        self.filename = filename

    def on_any_event(self, event):
        if basename(event.src_path) == self.filename:
            self.callback()


class TkViewer(tk.Frame):

    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.widget = None

    def run(self):
        observer = Observer()
        observer.schedule(TkHandler(self.update, FILE), DIR)
        observer.start()
        self.update()

    def update(self):
        self.clear()
        try:
            self.load()
            self.show_ui()
        except Exception as e:
            self.show_message(e)

    def clear(self):
        if self.widget is not None:
            self.widget.destroy()
            self.pack_forget()

    def load(self):
        try:
            self.ui = reload(self.ui)
        except AttributeError:
            self.ui = import_module(splitext(FILE)[0], DIR)

    def show_ui(self):
        self.widget = self.ui.Application(self.root)

    def show_message(self, e):
        widget = self.widget = tk.Message(self, text=str(e))
        widget.bind("<Configure>", lambda event: event.widget.config(width=self.root.winfo_width()))
        widget.pack(fill=BOTH, expand=True)
        self.pack(fill=BOTH, expand=True)


if __name__ == '__main__':
    try:
        windows_high_resolution()
    except:
        pass
    
    root = tk.Tk()
    root.attributes('-topmost', True)
    TkViewer(root).run()
    root.mainloop()
