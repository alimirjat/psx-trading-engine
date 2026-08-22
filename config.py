import os
from pathlib import Path
from kivy.app import App

APP_NAME = "PSX AI Intelligence"
APP_VERSION = "1.0.0"
DATABASE_NAME = "psx_ai_app.db"
API_TIMEOUT = int(os.getenv("PSX_AI_API_TIMEOUT", "30"))

WATCHLIST = ("POWER", "PAEL", "PAKRI", "NRL", "CNERGY", "ATRL", "SSGC")

GROK_API_KEY = os.getenv("GROK_API_KEY", "")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.6")


def app_data_dir(app=None):
    """Always prefer Kivy's Android-safe writable app directory."""
    try:
        running = app or App.get_running_app()
        if running and getattr(running, "user_data_dir", None):
            path = Path(running.user_data_dir)
            path.mkdir(parents=True, exist_ok=True)
            return path
    except Exception:
        pass

    # Desktop/dev fallback only.
    path = Path(os.environ.get("PSX_AI_DATA_DIR", Path.cwd() / ".psx_ai"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path(app=None):
    return app_data_dir(app) / DATABASE_NAME
