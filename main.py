import traceback

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from database import Database
from scheduler import Scheduler
from ui import ModernDashboard, BG


class ErrorScreen(Screen):
    def __init__(self, error_text, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=20, spacing=12)
        root.add_widget(Label(
            text="PSX AI STARTUP ERROR",
            font_size="20sp",
            bold=True,
            size_hint_y=None,
            height=45,
        ))
        root.add_widget(Label(
            text=error_text,
            font_size="11sp",
            halign="left",
            valign="top",
        ))
        self.add_widget(root)


class DashboardScreen(Screen):
    def __init__(self, scheduler, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(ModernDashboard(scheduler=scheduler))


class PSXAIApp(App):
    title = "PSX AI Intelligence"

    def build(self):
        Window.clearcolor = BG
        sm = ScreenManager()

        try:
            self.db = Database()
            self.scheduler = Scheduler(self.db)
            sm.add_widget(DashboardScreen(self.scheduler, name="dashboard"))
        except Exception as exc:
            error = traceback.format_exc()
            print(error)
            sm.add_widget(ErrorScreen(
                "Startup failed.\n\n" + str(exc) + "\n\n" + error,
                name="error"
            ))
        return sm

    def on_stop(self):
        try:
            if getattr(self, "db", None):
                self.db.close()
        except Exception:
            pass


if __name__ == "__main__":
    PSXAIApp().run()
