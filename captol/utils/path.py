from __future__ import annotations
from ctypes import windll
from os.path import basename, splitext
from win32api import EnumDisplayMonitors


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