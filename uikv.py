from ctypes import windll

from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.properties import StringProperty

from memory import Environment


def high_resolution() -> None:
    windll.shcore.SetProcessDpiAwareness(True)


class Tab(TabbedPanel):
    folder = StringProperty()
    
    def __init__(self, env, **kwargs):
        super().__init__(**kwargs)
        self.folder = env.default_folder


class MainApp(App):

    def build(self):
        env = Environment.load()
        return Tab(env)


if __name__ == '__main__':
    high_resolution()
    MainApp().run()