from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget


BG = (0.025, 0.035, 0.065, 1)
CARD = (0.055, 0.075, 0.125, 1)
TEXT = (0.94, 0.96, 1.0, 1)
MUTED = (0.55, 0.60, 0.70, 1)
ACCENT = (0.20, 0.72, 1.0, 1)
GREEN = (0.25, 0.86, 0.58, 1)
AMBER = (1.0, 0.68, 0.25, 1)
RED = (1.0, 0.32, 0.38, 1)


class Card(BoxLayout):
    def __init__(self, bg=CARD, radius=16, **kwargs):
        super().__init__(**kwargs)
        self.padding = dp(13)
        self.spacing = dp(7)
        with self.canvas.before:
            self._color = Color(*bg)
            self._rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(radius)]
            )
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class Pill(Label):
    def __init__(self, text="READY", bg=GREEN, **kwargs):
        super().__init__(text=text, color=TEXT, bold=True, font_size="9sp",
                         size_hint=(None, None), size=(dp(86), dp(28)),
                         halign="center", valign="middle", **kwargs)
        self.text_size = self.size
        with self.canvas.before:
            self._color = Color(*bg)
            self._rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(14)]
            )
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class Metric(Card):
    def __init__(self, title, value="--", caption="WAITING", **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None,
                         height=dp(105), **kwargs)
        self.add_widget(Label(text=title, color=MUTED, font_size="9sp",
                              bold=True, size_hint_y=None, height=dp(20),
                              halign="left"))
        self.add_widget(Label(text=value, color=TEXT, font_size="23sp",
                              bold=True, halign="left"))
        self.add_widget(Label(text=caption, color=MUTED, font_size="8sp",
                              size_hint_y=None, height=dp(18), halign="left"))


class ModernDashboard(BoxLayout):
    def __init__(self, scheduler, **kwargs):
        super().__init__(orientation="vertical", padding=(dp(9), dp(7), dp(9), 0),
                         spacing=dp(7), **kwargs)
        self.scheduler = scheduler

        header = BoxLayout(size_hint_y=None, height=dp(58))
        title = BoxLayout(orientation="vertical")
        title.add_widget(Label(text="PSX AI", color=TEXT, font_size="21sp",
                               bold=True, halign="left"))
        title.add_widget(Label(text="BEASTMODE INTELLIGENCE",
                               color=ACCENT, font_size="8sp", halign="left"))
        header.add_widget(title)
        header.add_widget(Pill("SYSTEM READY", GREEN))
        self.add_widget(header)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(2))
        body = BoxLayout(orientation="vertical", spacing=dp(8),
                         size_hint_y=None, padding=(0, 0, 0, dp(10)))
        body.bind(minimum_height=body.setter("height"))

        hero = Card(bg=(0.045, 0.10, 0.17, 1),
                    orientation="vertical", size_hint_y=None, height=dp(126))
        hero.add_widget(Label(text="Evidence-first market intelligence",
                              color=TEXT, font_size="15sp", bold=True,
                              halign="left"))
        hero.add_widget(Label(
            text="INTRADAY  •  SWING  •  LONG-TERM  •  5X WATCH",
            color=ACCENT, font_size="9sp", halign="left"))
        hero.add_widget(Label(
            text="Signals stay locked until source data is independently verified.",
            color=MUTED, font_size="9sp", halign="left"))
        self.scan = Button(
            text="RUN VERIFIED MARKET SCAN",
            background_normal="",
            background_color=ACCENT,
            color=TEXT,
            bold=True,
            font_size="11sp",
            size_hint_y=None,
            height=dp(38),
        )
        self.scan.bind(on_release=self.run_scan)
        hero.add_widget(self.scan)
        body.add_widget(hero)

        body.add_widget(Label(text="MARKET PULSE",
                              color=TEXT, font_size="14sp", bold=True,
                              size_hint_y=None, height=dp(27), halign="left"))
        row = BoxLayout(spacing=dp(7), size_hint_y=None, height=dp(105))
        row.add_widget(Metric("LIVE MARKET", "--", "NOT VERIFIED"))
        row.add_widget(Metric("HISTORY", "--", "NOT LOADED"))
        body.add_widget(row)

        body.add_widget(Label(text="STRATEGY RADAR",
                              color=TEXT, font_size="14sp", bold=True,
                              size_hint_y=None, height=dp(27), halign="left"))

        for title, detail, accent in (
            ("⚡  INTRADAY", "Momentum • volume • liquidity • breakout", ACCENT),
            ("↗  SWING", "Trend • catalyst • historical pattern", GREEN),
            ("◈  LONG-TERM / 5X", "Fundamentals • valuation • macro • risk", AMBER),
        ):
            c = Card(orientation="horizontal", size_hint_y=None, height=dp(66))
            c.add_widget(Label(text=title, color=accent, font_size="12sp",
                               bold=True, size_hint_x=None, width=dp(125),
                               halign="left"))
            c.add_widget(Label(text=detail, color=MUTED, font_size="9sp",
                               halign="left"))
            body.add_widget(c)

        body.add_widget(Label(text="VERIFICATION PIPELINE",
                              color=TEXT, font_size="14sp", bold=True,
                              size_hint_y=None, height=dp(27), halign="left"))

        pipe = Card(orientation="vertical", size_hint_y=None, height=dp(137))
        for text, color in (
            ("01  DATA SOURCES", ACCENT),
            ("02  CROSS-SOURCE VERIFICATION", GREEN),
            ("03  TECHNICAL + FUNDAMENTAL", GREEN),
            ("04  NEWS + MACRO + GEOPOLITICS", AMBER),
            ("05  AI RED-TEAM + DECISION", RED),
        ):
            pipe.add_widget(Label(text="●  " + text, color=color,
                                  font_size="9sp", size_hint_y=None,
                                  height=dp(23), halign="left"))
        body.add_widget(pipe)

        self.message = Label(
            text="System ready • no unverified signal will be shown.",
            color=MUTED, font_size="9sp", size_hint_y=None, height=dp(34),
            halign="center")
        body.add_widget(self.message)

        scroll.add_widget(body)
        self.add_widget(scroll)

        nav = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(5))
        for text in ("OVERVIEW", "SCANNER", "SETTINGS"):
            b = Button(text=text, background_normal="",
                       background_color=(0.055, 0.075, 0.125, 1),
                       color=TEXT, font_size="9sp")
            if text == "SCANNER":
                b.bind(on_release=self.run_scan)
            nav.add_widget(b)
        self.add_widget(nav)

    def run_scan(self, *_):
        self.scan.disabled = True
        self.message.text = "Checking authoritative PSX source..."
        try:
            result = self.scheduler.run_market_scan()
            self.message.text = result.get("message", "Scan completed.")
        except Exception as exc:
            self.message.text = "Scan failed safely: " + str(exc)
        finally:
            Clock.schedule_once(self._enable_scan, 0.5)

    def _enable_scan(self, *_):
        self.scan.disabled = False
