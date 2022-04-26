from __future__ import annotations
from dataclasses import dataclass, asdict
import json
from os import makedirs
from os.path import dirname
from typing import Literal

from captol.utils.const import ENV_FILE, AREA_FILE


class AreaDB:

    def __init__(self, env: Environment) -> None:
        self.areas = None
        self.env = env
        self.is_edited = False

        try:
            dict_areas = self._read_filedata()
        except FileNotFoundError as e:
            dict_areas = self._load_defaults()
        self._store_astype_rect(dict_areas)

    @property
    def namelist(self) -> list[str]:
        return list(self.areas.keys())

    def save(self) -> None:
        dict_areas = self._fetch_astype_dict()
        self._write_filedata(dict_areas)

    def get(self, name: str) -> Rectangle:
        return self.areas[name]

    def write(self, name: str, rect: Rectangle) -> None:
        self.areas[name] = rect
        self.areas = dict(sorted(self.areas.items()))

    def delete(self, name: str) -> None:
        del self.areas[name]

    def has_name(self, name: str) -> bool:
        names = self.areas.keys()
        return name in names

    def _read_filedata(self) -> dict[dict]:
        with open(self.env.area_file, 'r') as f:
            dict_areas = json.load(f)
        return dict_areas

    def _write_filedata(self, dict_areas: dict[dict]) -> None:
        savepath = self.env.area_file
        makedirs(dirname(savepath), exist_ok=True)
        with open(savepath, 'w') as f:
            json.dump(dict_areas, f, indent=4)

    def _load_defaults(self) -> dict[dict]:
        return {"edit me": {"x": 400, "y": 300, "w": 800, "h": 600}}

    def _store_astype_rect(self, dict_areas: dict[dict]) -> None:
        rect_areas = dict()
        for name, dict_area in dict_areas.items():
            rect_areas[name] = Rectangle(**dict_area)
        self.areas = dict(sorted(rect_areas.items()))

    def _fetch_astype_dict(self) -> dict[dict]:
        dict_areas = dict()
        for name, rect_area in self.areas.items():
            dict_areas[name] = asdict(rect_area)
        return dict_areas


@dataclass
class Rectangle:
    x: int
    y: int
    w: int
    h: int


@dataclass
class Environment:
    theme: str = "darkly"
    area_file: str = AREA_FILE
    default_save_folder: str = "C:/Users/hnlPublic/Desktop"
    pixel_difference_threshold: int = 10000
    image_duplication_check_steps: int = 1
    auto_clip_interval: float = 1.0
    compress_before_pdf_conversion: bool = True
    compression_ratio: int = 85
    resize_before_pdf_conversion: bool = False
    resized_height: int = 720
    zip_converted_images: bool = True
    password_security_level: Literal[1, 2, 3] = 3

    def __post_init__(self) -> None:
        self.load()

    def load(self) -> None:
        try:
            with open(ENV_FILE, 'r') as f:
                jsondict = json.load(f)
            self._set_data(jsondict)
        except Exception:
            pass

    def save(self) -> None:
        makedirs(dirname(ENV_FILE), exist_ok=True)
        with open(ENV_FILE, 'w') as f:
            json.dump(asdict(self), f, indent=4)

    def _set_data(self, jsondict: dict) -> None:
        for name, var in jsondict.items():
            self.__setattr__(name, var)
