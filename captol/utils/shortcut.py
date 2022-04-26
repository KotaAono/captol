import os
from typing import List
import win32com.client

import captol
from captol.utils.const import ICON_FILE


VBS_PATH = os.path.join(str(captol.__path__[0]), 'captol.vbs')


def conda_activate_cmd(conda_path: str, env_name: str) -> str:
    activator = os.path.abspath(
        os.path.join(conda_path, 'Scripts','activate.bat'))
    env_path = os.path.abspath(
        os.path.join(conda_path, 'envs', env_name))
    return f'{activator} {env_path}'


def create_vbs(precmds: List[str] = []) -> None:
    pycmd = f'python -m captol'
    precmds.append(pycmd)
    cmds = [
        'Dim ws',
        'Set ws = CreateObject("WScript.Shell")',
        f'ws.Run "cmd /c {" && ".join(precmds)}", vbhide'
    ]

    with open(VBS_PATH, 'w') as f:
        for cmd in cmds:
            f.write(cmd)
            f.write('\n')


def create_shortcut(dir_: str) -> None:
    if not os.path.isdir(dir_):
        print('Directory not found.')

    lnk_path = os.path.join(dir_, 'Captol.lnk')
    ws = win32com.client.Dispatch("WScript.Shell")
    sc = ws.CreateShortCut(lnk_path)
    sc.Targetpath = VBS_PATH
    sc.Description = "A python-based GUI application for reconstructing screen-sharing documents."
    sc.IconLocation = ICON_FILE
    sc.save()


def check_directory(dir_: str) -> None:
    if not os.path.isdir(dir_):
        print(f'Directory "{dir_}" not found.')
        return


def run() -> None:
    ans = input('Do you use via anaconda environment? [y/n]: ')
    if ans in ('y', 'Y'):
        c_path = input('Input path to anaconda3 directory: ')
        check_directory(c_path)

        envs = {i: env for i, env in enumerate(os.listdir(os.path.join(c_path, 'envs')))}
        n = int(input(f'Select environment {envs}: '))
        cmds = conda_activate_cmd(c_path, envs[n])
        create_vbs(precmds=[cmds])
    elif ans in ('n', 'N'):
        create_vbs()
    else:
        run()

    s_path = input('Input directory path where you want to put shortcut: ')
    check_directory(s_path)
    create_shortcut(s_path)
