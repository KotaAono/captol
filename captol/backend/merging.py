from __future__ import annotations
import io
import os
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED
from PIL import Image

import img2pdf

from captol.backend.data import Environment


class PdfConverter:

    def __init__(self, env: Environment):
        self.env = env

    def save_as_pdf(self, image_paths: tuple[str], savepath: str) -> None:
        savedir, savename = os.path.split(savepath)
        savename_noext = os.path.splitext(savename)[0]

        zip_dir = os.path.join(savedir, 'archives')
        pdf = self._fetch_images_as_pdf(image_paths)
        self._dump_in_pdf(pdf, savedir, savename_noext)
        if self.env.zip_converted_images:
            self._pack_usedimages_into_zip(image_paths, zip_dir, savename_noext)

    def _fetch_images_as_pdf(self, image_paths: list[str]) -> bytes:
        do_compress = self.env.compress_before_pdf_conversion
        quality = self.env.compression_ratio
        do_resize = self.env.resize_before_pdf_conversion
        height = self.env.resized_height

        images = list()
        for path in image_paths:
            try:
                image = Image.open(path)
                if do_resize:
                    image = self._resize(image, height)
                if do_compress:
                    image = self._compress(image, quality)
                images.append(image)
            except FileNotFoundError:
                pass

        return img2pdf.convert(images)

    def _resize(self, image: Image, height: int) -> Image:
        ratio = height / image.height
        width = round(image.width * ratio)
        return image.resize((width, height), resample=Image.BICUBIC)

    def _compress(self, image: Image, quality: int) -> Image:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()

    def _dump_in_pdf(self, pdf: bytes, output_dir: str, basename: str) -> None:
        output_path = os.path.join(output_dir, basename+'.pdf')
        with open(output_path, 'ab') as f:
            f.write(pdf)

    def _pack_usedimages_into_zip(
        self, image_paths: list[str], output_dir: str, basename: str) -> None:
        output_path = os.path.join(output_dir, basename+'.zip')
        os.makedirs(output_dir, exist_ok=True)

        self._create_zip(image_paths, output_path)
        self._remove_packed_images(image_paths)

    def _create_zip(self, image_paths: list[str], output_path: str):
        if os.path.isfile(output_path):
            try:
                os.remove(output_path)
            except FileNotFoundError:
                pass

        with ZipFile(output_path, 'a') as zf:
            for path in image_paths:
                try:
                    zf.write(
                        path, os.path.basename(path), compress_type=ZIP_DEFLATED)
                except FileNotFoundError:
                    pass

    def _remove_packed_images(self, image_paths: list[str]) -> None:
        for path in image_paths:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass


class PassLock:

    def __init__(self, env: Environment):
        self.env = env

    def encrypt(self, pdfpath: str, savepath: str, pw: str):
        lv = self._key_length()
        if pdfpath != savepath:
            self._run(
                f'qpdf --encrypt {pw} {pw} {lv} -- "{pdfpath}" "{savepath}"')
        else:
            self._run(
                f'qpdf --encrypt {pw} {pw} {lv} -- --replace-input "{pdfpath}"')

    def decrypt(self, pdfpath: str, savepath: str, pw: str):
        if pdfpath != savepath:
            self._run(
                f'qpdf --password={pw} --decrypt "{pdfpath}" "{savepath}"')
        else:
            self._run(
                f'qpdf --password={pw} --decrypt --replace-input "{pdfpath}"')

    def check_encryption(self, pdfpath: str) -> bool:
        try:
            self._run(f'qpdf --is-encrypted "{pdfpath}"')
            return True
        except Exception:
            return False

    def _run(self, command: str) -> None:
        output = subprocess.run(command, capture_output=True)
        if output.returncode == 2:
            raise Exception(output.stderr.decode())

    def _key_length(self) -> str:
        lv = self.env.password_security_level
        if lv == 1:
            return '40'
        elif lv == 2:
            return '128'
        elif lv == 3:
            return '256'
        else:
            raise ValueError(f'Security level must be 1, 2 or 3, not {lv}.')