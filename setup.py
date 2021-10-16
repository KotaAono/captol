import sys
from cx_Freeze import setup, Executable

base = None

# GUI=有効, CUI=無効 にする
if sys.platform == 'win32':
    base = 'Win32GUI'

# exe にしたい python ファイルを指定
exe = Executable(script='uitk.py',
                 base=base,
                 icon='favicon.ico')

options = {
    'build_exe': {
        'includes': [
            'data',
            'extraction',
            'merging'
        ],
        'path': sys.path + ['backend']
    }
}

# セットアップ
setup(name='Captol',
      version='1.0',
      description='Captol is a python-based GUI application for reconstructing screen-sharing documents.',
      options=options,
      executables=[exe])