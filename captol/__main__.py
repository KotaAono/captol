from argparse import ArgumentParser


parser = ArgumentParser()
parser.add_argument(
    '-c', '--create-shortcut', action='store_true',
    help='Create shortcut.')
parser.add_argument(
    '-d', '--devel-mode', action='store_true',
    help='Run application in developer mode.')

args = parser.parse_args()
create_sc: bool = args.create_shortcut
devel_mode: bool = args.devel_mode

if create_sc:
    from captol.utils import shortcut
    shortcut.run()
else:
    if not devel_mode:
        from captol.frontend import ui
        ui.run()
    else:
        from captol.devel import viewer
        viewer.run()
