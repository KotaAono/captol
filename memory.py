from __future__ import annotations
from dataclasses import dataclass, asdict
import json
from typing import Literal


ENV_FILE = 'env.json'


class AreaDB:

    def __init__(self, env: Environment) -> None:
        self.areas = None
        self.env = env
        self.is_edited = False

        try:
            dict_areas = self._read_filedata()
        except FileNotFoundError as e:
            print(e)
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
        with open(self.env.area_file, 'w') as f:
            json.dump(dict_areas, f, indent=4)

    def _load_defaults(self) -> dict[dict]:
        return self.env.default_areas

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
    area_file: str
    default_areas: dict
    default_folder: str
    image_difference_threshold: int
    enalbe_active_image_saver: bool
    autoclip_interval: float
    enable_pdf_compression: bool
    compression_ratio: int
    preseve_images_in_zip: bool
    use_common_password: bool
    common_password: str
    password_security_level: Literal[1, 2, 3]

    @classmethod
    def load(cls) -> Environment:
        default = dict(
            area_file = './areas.json',
            default_areas = {'fullscreen': {'x': 0, 'y': 0, 'w': 1920, 'h': 1080}},
            default_folder = 'C:/Users/hnlPublic/Desktop',
            image_difference_threshold = 1000,
            enalbe_active_image_saver = True,
            autoclip_interval = 1.0,
            enable_pdf_compression = True,
            compression_ratio = 85,
            preseve_images_in_zip = True,
            use_common_password = True,
            common_password = "conf",
            password_security_level = 2
        )

        try:
            with open(ENV_FILE, 'r') as f:
                settings = json.load(f)
            instance = cls(**settings)
        except Exception as e:
            print(e)
            instance = cls(**default)
        return instance

    def save(self) -> None:
        with open(ENV_FILE, 'w') as f:
            json.dump(asdict(self), f, indent=4)
