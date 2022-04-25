from __future__ import annotations
import tkinter as tk
from tkinter import BOTH, DISABLED, NORMAL, CENTER
from tkinter import ttk
from tkinter import filedialog, messagebox

from .mainframe import Application
from .subframe import ProgressWindow
from .utils import append_ext, noext_basename, shorten
from ..backend.data import Environment
from ..backend.merging import PdfConverter, PassLock


class MergeTab(ttk.Frame):

    def __init__(
        self, root: tk.Tk, parent: Application, env: Environment) -> None:
        super().__init__(root)
        self.root = root
        self.image_paths = None
        self.pdf_path = None
        self.var_nimages_total = tk.IntVar()
        self.var_imagename_from = tk.StringVar()
        self.var_imagename_to = tk.StringVar()
        self.var_pdfpath = tk.StringVar()
        self.var_pwd1 = tk.StringVar()
        self.var_pwd2 = tk.StringVar()
        self.converter = PdfConverter(env)
        self.passlock = PassLock(env)

        self._create_widgets()
        self._init_vars_conversion()
        self._init_vars_protection()

    def block_widgets(self) -> None:
        for widget in self.winfo_children():
            try:
                widget['state'] = DISABLED
            except tk.TclError:
                pass

    def release_widgets(self) -> None:
        for widget in self.winfo_children():
            try:
                if widget.winfo_name() in ('!entry', '!entry2', '!entry3'):
                    widget['state'] = 'readonly'
                else:
                    widget['state'] = NORMAL
            except tk.TclError:
                pass

    def _create_widgets(self) -> None:
        ttk.LabelFrame(
            self,
            text="PDF conversion").place(x=10, y=10, width=435, height=130)
        ttk.Button(
            self, text="📁", style='secondary.Outline.TButton',
            command=self._on_imagefolder_clicked).place(x=30, y=50, width=45)
        ttk.Entry(
            self, textvariable=self.var_imagename_from,
            state='readonly').place(x=80, y=50, width=160, height=37)
        ttk.Label(self, text="–").place(x=246, y=52)
        ttk.Entry(
            self, textvariable=self.var_imagename_to,
            state='readonly').place(x=267, y=50, width=160, height=37)
        ttk.Label(self, text="Total images:").place(x=30, y=100)
        ttk.Label(
            self, textvariable=self.var_nimages_total,
            anchor=CENTER).place(x=200, y=100, width=200)
        ttk.Button(
            self, text="Convert",
            command=self._on_convert_clicked).place(x=150, y=155, width=160)
        ttk.LabelFrame(
            self, text="Password protection").place(
                x=10, y=200, width=435, height=200)
        ttk.Button(
            self, text="📁", style='secondary.Outline.TButton',
            command=self._on_pdffolder_clicked).place(x=30, y=240, width=45)
        ttk.Entry(
            self, textvariable=self.var_pdfpath,
            state='readonly').place(x=80, y=240, width=345, height=37)
        ttk.Label(self, text="Password:").place(x=30, y=300)
        ent_pwd1 = self.ent_pwd1 = ttk.Entry(self, textvariable=self.var_pwd1)
        ent_pwd1.place(x=145, y=295, width=280, height=37)
        ttk.Label(self, text="Again:").place(x=30, y=350)
        ent_pwd2 = self.ent_pwd2 = ttk.Entry(
            self, show="●", textvariable=self.var_pwd2)
        ent_pwd2.place(x=145, y=345, width=280, height=37)
        btn_lock = self.btn_lock = ttk.Button(self)
        btn_lock.place(x=150, y=415, width=160)
        self.pack(fill=BOTH, expand=True)

    def _init_vars_conversion(self) -> None:
        self.var_imagename_from.set("")
        self.var_imagename_to.set("")
        self.var_nimages_total.set(0)
        self.image_paths = None

    def _init_vars_protection(self) -> None:
        self.var_pdfpath.set("")
        self.var_pwd1.set("")
        self.var_pwd2.set("")
        self.ent_pwd1['show'] = "●"
        self.btn_lock['text'] = "Lock/Unlock"
        self.btn_lock['command'] = lambda: None
        self.pdf_path = None

    def _on_imagefolder_clicked(self) -> None:
        images = filedialog.askopenfilenames(
            title="Select Images", filetypes=[('png', '*.png')])
        if not images:
            return

        self.var_imagename_from.set(noext_basename(images[0]))
        if len(images) > 1:
            self.var_imagename_to.set(noext_basename(images[-1]))
        else:
            self.var_imagename_to.set("")
        self.var_nimages_total.set(len(images))
        self.image_paths = images

    def _on_convert_clicked(self) -> None:
        if self.image_paths is None:
            return
        savepath = filedialog.asksaveasfilename(
            title="Save as", filetypes=[('pdf', '*.pdf')])
        if not savepath:
            return
        savepath = append_ext(savepath, '.pdf')

        self.block_widgets()
        with ProgressWindow(
            self, "PDF Conversion", "Packing images into a pdf...") as pb:
            pb.during(self.converter.save_as_pdf, self.image_paths, savepath)
            pb.after(self._init_vars_conversion)
            pb.final(self.release_widgets)

    def _on_pdffolder_clicked(self) -> None:
        pdf_path = filedialog.askopenfilename(
            title="Select PDF", filetypes=[('pdf', '*.pdf')])
        if not pdf_path:
            return

        self._init_vars_protection()
        self.pdf_path = pdf_path
        self.var_pdfpath.set(shorten(pdf_path, maxlen=2))
        if self.passlock.check_encryption(pdf_path):
            self.ent_pwd1['show'] = ""
            self.ent_pwd2.place_forget()
            self.btn_lock['text'] = "Unlock"
            self.btn_lock['command'] = self._unlock
        else:
            self.ent_pwd1['show'] = "●"
            self.ent_pwd2.place(x=145, y=365, width=280, height=37)
            self.btn_lock['text'] = "Lock"
            self.btn_lock['command'] = self._lock

    def _lock(self) -> None:
        pdfpath = self.pdf_path
        if pdfpath is None:
            return
        pwd1, pwd2 = self.var_pwd1.get(), self.var_pwd2.get()
        if not self._verify(pwd1, pwd2):
            return
        savepath = filedialog.asksaveasfilename(
            title="Save as", filetypes=[('pdf', '*.pdf')])
        if not savepath:
            return
        savepath = append_ext(savepath, '.pdf')

        self.block_widgets()
        with ProgressWindow(
            self, "Password Protection", "Trying to encrypt...") as pb:
            pb.during(self.passlock.encrypt, pdfpath, savepath, pwd1)
            pb.after(self._init_vars_protection)
            pb.final(self.release_widgets)

    def _unlock(self) -> None:
        pdfpath = self.pdf_path
        if pdfpath is None:
            return
        pwd1 = self.var_pwd1.get()
        if not self._verify(pwd1):
            return

        self.block_widgets()
        with ProgressWindow(
            self, "Password Protection", "Trying to decrypt...") as pb:
            pb.during(self.passlock.decrypt, pdfpath, pdfpath, pwd1)
            pb.after(self._init_vars_protection)
            pb.final(self.release_widgets)

    def _verify(self, pwd1: str, pwd2: str = None) -> bool:
        if pwd1 == "":
            messagebox.showerror(
                "Invalid input", "Enter a password in first entry box.")
            return False
        elif pwd2 is not None and pwd1 != pwd2:
            messagebox.showerror(
                "Invalid input",
                "Enter the same password in the second entry box.")
            return False
        return True

