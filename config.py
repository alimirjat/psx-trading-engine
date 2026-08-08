"""PSX Trading Engine — FINAL CONFIGURATION"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "cache")
LOG_DIR = os.path.join(BASE_DIR, "logs")
PORTFOLIO_FILE = os.path.join(BASE_DIR, "data", "portfolio.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)

# ========== TIMING SETTINGS ==========
PRICE_CHECK_INTERVAL = 30
DASHBOARD_REFRESH = 60
SIGNAL_CHECK_INTERVAL = 60
FULL_ANALYSIS_INTERVAL = 300
DAILY_SUMMARY_TIME = "16:00"
NEWS_CHECK_INTERVAL = 600

# ========== ALERT THRESHOLDS ==========
TELEGRAM_ALERT_MIN_SCORE = 75
STOP_LOSS_ALERT = True
TARGET_HIT_ALERT = True

# ========== INDICATORS ==========
INDICATORS = {
    "SMA": [20, 50, 200],
    "EMA": [12, 26],
    "RSI_PERIOD": 14,
    "MACD_FAST": 12,
    "MACD_SLOW": 26,
    "MACD_SIGNAL": 9,
    "BB_PERIOD": 20,
    "BB_STD": 2,
    "ATR_PERIOD": 14,
    "SUPERTREND_PERIOD": 10,
    "SUPERTREND_MULTIPLIER": 3,
    "ADX_PERIOD": 14,
    "MFI_PERIOD": 14,
    "CCI_PERIOD": 20,        # <-- FIXED: Added missing CCI_PERIOD
}

# ========== SCREENER ==========
SCREENER_CONFIG = {
    "MIN_PRICE": 5.0,
    "MAX_PRICE": 5000.0,
    "MIN_VOLUME": 1000,
    "MIN_RS_SCORE": 50,
    "TREND_FILTERS": {
        "sma20_above_sma50": True,
        "price_above_sma20": True,
        "rsi_range": (30, 70),
        "macd_bullish": True,
    }
}

# ========== SIGNAL ENGINE ==========
SIGNAL_CONFIG = {
    "STRONG_BUY_MIN": 75,
    "BUY_MIN": 60,
    "HOLD_MIN": 45,
    "SELL_MIN": 30,
    "RSI_OVERSOLD": 30,
    "RSI_OVERBOUGHT": 70,
    "MIN_VOLUME_RATIO": 1.2,
    "MIN_RR_RATIO": 1.5,
    "NEWS_CHECK_BEFORE_BUY": True,
    "MIN_NEWS_SENTIMENT": 0.3,
}

# ========== GROK 4.5 API (x.ai) ==========
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
GROK_API_URL = os.getenv("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.5")

# ========== NEWS API ==========
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"

# ========== TELEGRAM BOT ==========
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ========== PORTFOLIO ==========
MAX_POSITIONS = 10
DEFAULT_POSITION_SIZE = 100
CAPITAL_PER_TRADE = 50000

# ========== WATCHLIST ==========
WATCHLIST = [
    "POWER", "NRL", "LUCK", "FFC", "MARI",
    "HASCOL", "MLCF", "PSO", "HUBC", "ATRL",
    "EFERT", "UNITY", "OGDC", "PPL", "ENGRO",
    "TRG", "SYS", "NETSOL", "PAEL", "DCL"
]
