import os
import sys
from cx_Freeze import setup, Executable

base = None

# GUI=有効, CUI=無効 にする
if sys.platform == 'win32':
    base = 'Win32GUI'
    os.environ['TCL_LIBRARY'] = "C:\\Users\\hnlPublic\\anaconda3\\envs\\appdev38\\tcl\\tcl8.6"
    os.environ['TK_LIBRARY'] = "C:\\Users\\hnlPublic\\anaconda3\envs\\appdev38\\tcl\\tk8.6"


exe = Executable(script='uitk.py',
                 base=base,
                 icon='favicon.ico',
                 target_name='Captol')

options = {
    'build_exe': {
        'packages': [],
        'includes': [
            '__future__',
            'ctypes',
            'dataclasses',
            'os',
            'threading',
            'time',
            'tkinter',
            'typing',
            'win32api',
            'ttkbootstrap',
            'json',
            'collections',
            'datetime',
            'pathlib',
            'PIL',
            're',
            'cv2',
            'numpy',
            'io',
            'subprocess',
            'zipfile',
            'img2pdf',
            'data',
            'extraction',
            'merging'
        ],
        'excludes': [
            'asyncio',
            'concurrent',
            'email',
            'html',
            'http',
            'ipykernel',
            'IPython',
            'ipython_genutils',
            'jedi',
            'ninja2',
            'jupyter_client',
            'jupyter_core',
            'lib2to3',
            'markupsafe',
            'matplotlib',
            'matplotlib_inline',
            'msilib',
            'multiprocessing',
            'olefile',
            'parso',
            'psutil',
            'pygments'
            'PyQt5',
            'setuptools',
            'sqlite3',
            'tornado',
            'unittest'
            'xml',
            'xmlrpc'
        ]
    }
}  # logging, urllib should not be excluded

# セットアップ
setup(name='Captol',
      version='1.0',
      description='Captol is a python-based GUI application for reconstructing screen-shared documents.',
      options=options,
      executables=[exe])