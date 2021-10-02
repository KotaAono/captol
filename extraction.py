from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from datetime import date
from glob import iglob, glob
import os
import pathlib
from typing import final
from PIL import Image, ImageGrab
import re
import tkinter as tk

import cv2
import numpy as np
from memory import Rectangle, Environment


class Clipper:

    def __init__(self) -> None:
        self.area = None

    def register(self, area: Rectangle) -> None:
        self.area = area
    
    def clip(self) -> Image:
        area = self.area
        x1, y1 = area.x, area.y
        x2, y2 = x1 + area.w, y1 + area.h
        image = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        return image


class ImageCounter:

    def __init__(self, ext: str, var_past: tk.IntVar, var_today: tk.IntVar) -> None:
        self.ext = ext
        self.var_past = var_past
        self.var_today = var_today
        self.basedir = None
        self.date = None
        self.lastnum = None

        self._set_stemname()

    def next_savepath(self) -> str:
        nextnum = self._advance_num()
        name = f'{self.date}_{nextnum}.{self.ext}'
        path = os.path.join(self.basedir, name)
        if os.path.isfile(path):
            self.next()
        return path

    def change_dir(self, basedir: str) -> None:
        self.basedir = basedir

    def up(self, value: int) -> None:
        self.var_today.set(self.var_today.get() + value)

    def down(self, value: int) -> None:
        self.var_today.set(self.var_today.get() - value)

    def initialize_count(self) -> int:
        date_pattern = re.compile('(\d{4})-(\d{2})-(\d{2})_(\d+)\.')
        today_pattern = re.compile(f'{self.date}_(\d+)\.')
        num_pattern = re.compile('_(\d+)\.')
        dirimages = pathlib.Path(self.basedir).glob(f'*.{self.ext}')
        matchnames = [p.name for p in dirimages if date_pattern.match(p.name)]
        todaynums = [int(num_pattern.findall(p)[0]) for p in matchnames if today_pattern.match(p)]

        n_today = len(todaynums)
        n_past = len(matchnames) - n_today
        self.var_past.set(n_past)
        self.var_today.set(n_today)
        self.lastnum = max(todaynums+[0])
    
    def _set_stemname(self) -> None:
        today = format(date.today())
        self.date = today

    def _advance_num(self) -> int:
        nextnum = self.lastnum + 1
        self.lastnum = nextnum
        return nextnum


class ImageBuffer:

    def __init__(self, env: Environment) -> None:
        self.env = env
        self.q = deque(maxlen=2)
        self.new = None

    def hold(self, image: Image) -> None:     
        self.new = PathAssignedImage(image)
    
    def release(self) -> None:        
        self.new = None

    def save(self, path: str) -> None:
        if self.new is None:
            raise Exception('No object to save. Hold it first.')

        new = self.new
        new.color.save(path)
        new.path = path
        self.q.append(new)
        self.release()

    def delete(self, past_step: int) -> None:
        idx = -past_step
        target = self.q[idx]
        try:
            os.remove(target.path)
        except FileNotFoundError:
            pass
        finally:
            del self.q[idx]
    
    def compare_similarity(self, past_step: int) -> bool:
        if self.new is None:
            raise Exception('No object to compare. Hold new image first.')
        
        if past_step > len(self.q):
            return False
        
        idx = -past_step
        target = self.q[idx]
        new = self.new
        
        pix = self._calculate_different_pixels(new.gray, target.gray)
        if pix > self.env.image_difference_threshold:
            return False
        return True
    
    def _calculate_different_pixels(self, gray_image1: Image, gray_image2: Image) -> float:
        dif = cv2.absdiff(gray_image1, gray_image2)
        blr = cv2.GaussianBlur(dif, (15, 15), 5)
        thr = cv2.threshold(blr, 50, 255, cv2.THRESH_BINARY)[1]
        pix = np.sum(thr) / 255
        return pix


@dataclass
class PathAssignedImage:
    color: Image
    path: str = None
    gray: Image = None

    def __post_init__(self) -> None:
        imarr = np.array(self.color)
        self.gray = cv2.cvtColor(imarr, 0)
