from __future__ import annotations
from os.path import basename, splitext, join, dirname
from win32api import EnumDisplayMonitors


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
