
from __future__ import annotations
from glob import glob
import json
import os
import random
from time import sleep
from typing import Any
import unittest

import numpy as np
import cv2

from memory import ENV_FILE, AreaDB, Rectangle, Environment
from extraction import Clipper, SequentialNamer, ImageBuffer
from storage import PdfConverter, PassLock


os.chdir('testfield')
ENV_FILE = 'env.json'
AREAS_FILE = 'areas.json'


def try_delfile(filename: str) -> None:
    try:
        os.remove(filename)
    except FileNotFoundError:
        pass


def load_json(filename: str) -> dict:
    with open(filename, 'r') as f:
        data = json.load(f)
    return data


def file_exists(filename: str) -> bool:
    return os.path.isfile(filename)


def get_pngpaths() -> list[str]:
    return glob('*.png')


class RandCircles:

    def __init__(self) -> None:
        self.name = "Sample"

    def __enter__(self):
        cv2.namedWindow(self.name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        return self

    def __exit__(self, exception_type: Any, exception_value: Any, traceback: Any):
        cv2.destroyAllWindows()

    def show(self, seed: int = None, duration: float = 0.001):
        if seed is not None:
            random.seed(seed)

        w, h = 1920, 1080
        n = random.randint(5, 10)
        image = np.zeros((h, w, 3), np.uint8)
        for _ in range(n):
            x = random.randint(0, w)
            y = random.randint(0, h)
            r = random.randint(50, 300)
            bgr = random.sample([0, 255, random.choice((0, 128, 255))], 3)
            cv2.circle(image, (x, y), r, bgr, -1)

        cv2.imshow(self.name, image)
        cv2.waitKey(int(duration*1000))


class TestEnvironment(unittest.TestCase):

    def setUp(self) -> None:
        try_delfile(ENV_FILE)

    def test_fileio(self) -> None:
        # load default and save it
        self.assertFalse(file_exists(ENV_FILE))
        env = Environment.load()
        env.save()
        self.assertTrue(file_exists(ENV_FILE))

        # reload from file
        Environment.load()

    def test_overwrite(self) -> None:
        env = Environment.load()
        env.default_areas['test'] = {'x': 10, 'y': 10, 'w': 100, 'h': 100}
        env.image_difference_threshold = 2000
        env.enalbe_active_image_saver = False
        env.common_password = "test"
        env.save()

        filedata = load_json(ENV_FILE)
        self.assertIn('test', filedata['default_areas'].keys())
        self.assertEqual(filedata['image_difference_threshold'], 2000)
        self.assertFalse(filedata['enalbe_active_image_saver'])
        self.assertEqual(filedata['common_password'], "test")


class TestAreaDB(unittest.TestCase):

    def setUp(self) -> None:
        try_delfile(ENV_FILE)
        try_delfile(AREAS_FILE)
        self.env = Environment.load()

    def test_fileio(self) -> None:
        # load default and save it
        self.assertFalse(file_exists(AREAS_FILE))
        db = AreaDB(self.env)
        db.load()
        db.save()
        self.assertTrue(file_exists(AREAS_FILE))

        # relaod from file
        db.load()

    def test_overwrite(self) -> None:
        db = AreaDB(self.env)
        db.load()

        # add
        rect1 = Rectangle(1, 2, 3, 4)
        db.edit("test", rect1)
        self.assertTrue(db.has_name("test"))
        self.assertEqual(db.get("test"), rect1)

        # edit
        rect2 = Rectangle(10, 20, 30, 40)
        db.edit("test", rect2)
        self.assertEqual(db.get("test"), rect2)

        # delete
        db.delete("test")
        self.assertFalse(db.has_name("test"))


class TestImageSave(unittest.TestCase):

    def setUp(self) -> None:
        env = Environment.load()
        db = AreaDB(env)
        db.load()
        area = db.get("fullscreen")
        self.clipper = Clipper(env, area)
        self.namer = SequentialNamer('png', '.')
        self.imbuffer = ImageBuffer(env)

    def test_normal_save(self):
        for _ in range(5):
            with RandCircles() as rc:
                rc.show(duration=0.1)
                self._normal_save()

    def test_active_save(self) -> None:
        # simulates start -> next -> back -> next -> next -> next
        # -> manual clip -> comment up -> comment down
        # finally seed [0, 1, 2, 3] images remain
        seeds = [0, 1, 0, 1, 2, 3, 3, 2, 3]
        for seed in seeds:
            with RandCircles() as rc:
                rc.show(duration=0.1, seed=seed)
                self._active_save()

    def _normal_save(self) -> None:
        image = self.clipper.clip()
        name = self.namer.next()
        image.save(name)

    def _active_save(self) -> None:
        image = self.clipper.clip()
        self.imbuffer.hold(image)

        if self.imbuffer.compare_similarity(past_step=1):
            self.imbuffer.release()
            return

        if self.imbuffer.compare_similarity(past_step=2):
            self.imbuffer.delete(past_step=2)
            self.imbuffer.delete(past_step=1)

        name = self.namer.next()
        self.imbuffer.save(name)


class TestPdf(unittest.TestCase):

    def setUp(self) -> None:
        try_delfile("test.pdf")
        self.env = Environment.load()

    def test_compressed_pdf(self) -> None:
        self.env.enable_pdf_compression = True
        self.env.compression_ratio = 60
        converter = PdfConverter(self.env)

        pngpaths = get_pngpaths()
        converter.save_as_pdf(pngpaths, "test.pdf")


class TestPasslock(unittest.TestCase):

    def setUp(self) -> None:
        self.env = Environment.load()

    def test_successful_lock_unlock(self):
        passlock = PassLock(self.env)
        passlock.try_lock("test.pdf", "pw_test.pdf", "test")
        passlock.try_unlock("pw_test.pdf", "nopw_test.pdf", "test")

if __name__ == '__main__':
    unittest.main(verbosity=1)
