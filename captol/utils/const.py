from os.path import join, dirname, abspath


def fullpath(*args) -> str:
    return abspath(join(*args)).replace('\\', '/')


ENV_FILE = fullpath(dirname( __file__), '..', 'cache', 'env.json')
ICON_FILE = fullpath(dirname(__file__), '..', 'icon', 'icon.ico')
AREA_FILE = fullpath(dirname(__file__), '..', 'cache', 'areas.json')
