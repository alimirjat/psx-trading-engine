"""
PSX Data Feed - Multiple sources for real data
Priority: psxdata -> PSX Web Scraping -> yfinance -> Cached data
"""

import pandas as pd
from datetime import datetime, timedelta
import os
import logging
import requests
from io import StringIO

# ------------------------------------------------------------------
# Import config
# ------------------------------------------------------------------
try:
    from config import *
except ImportError:
    pass

LOG_DIR = globals().get('LOG_DIR', '.')
DATA_DIR = globals().get('DATA_DIR', './data')
LIVE_CACHE_MINUTES = globals().get('LIVE_CACHE_MINUTES', 5)
HISTORY_YEARS = globals().get('HISTORY_YEARS', 5)
HIST_CACHE_DAYS = globals().get('HIST_CACHE_DAYS', 1)
WATCHLIST = globals().get('WATCHLIST', ["ENGRO", "LUCK", "HBL", "OGDC", "PSO"])

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "data_feed.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Try to import optional libraries
try:
    import psxdata
    PSXDATA_AVAILABLE = True
    logger.info("psxdata library loaded")
except ImportError:
    PSXDATA_AVAILABLE = False
    logger.info("psxdata not available - will use web scraping")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
    logger.info("yfinance library loaded")
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.info("yfinance not available")


class PSXDataFeed:
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = timedelta(minutes=LIVE_CACHE_MINUTES)
        self.data_source = "unknown"

    def _is_cache_valid(self, ticker):
        if ticker not in self.cache_time:
            return False
        age = datetime.now() - self.cache_time[ticker]
        return age < self.cache_duration

    # ========== SOURCE 1: psxdata (Best - Local PC) ==========
    def _get_live_psxdata(self, ticker):
        if not PSXDATA_AVAILABLE:
            return None
        try:
            df = psxdata.quote(ticker)
            if df is None or df.empty:
                return None
            q = df.iloc[0]
            def get_val(*keys):
                for k in keys:
                    if k in q.index:
                        v = q[k]
                        if pd.notna(v) and v != '':
                            return v
                return 0
            return {
                'Ticker': ticker,
                'Price': float(get_val('ldcp', 'close', 'price', 'last')),
                'Volume': int(get_val('volume', 'turnover', 'vol')),
                'Change': float(get_val('change', 'net_change', 'chg')),
                'ChangePercent': float(get_val('change_percent', 'pct_change', 'change%')),
                'Open': float(get_val('open', 'op')),
                'High': float(get_val('high', 'hi')),
                'Low': float(get_val('low', 'lo')),
                'PreviousClose': float(get_val('prev_close', 'ycp', 'ldcp')),
                'timestamp': datetime.now(),
                'source': 'psxdata-live'
            }
        except Exception as e:
            logger.error(f"psxdata live error for {ticker}: {e}")
            return None

    def _get_hist_psxdata(self, ticker, years=HISTORY_YEARS):
        if not PSXDATA_AVAILABLE:
            return None
        try:
            start_date = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            df = psxdata.stocks(ticker, start=start_date, end=end_date)
            if df is None or df.empty:
                return None
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            df.columns = [c.strip().capitalize() for c in df.columns]
            ohlcv_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            available_cols = [c for c in ohlcv_cols if c in df.columns]
            if available_cols:
                df = df[available_cols]
            df.sort_index(inplace=True)
            return df
        except Exception as e:
            logger.error(f"psxdata hist error for {ticker}: {e}")
            return None

    # ========== SOURCE 2: PSX Website Scraping ==========
    def _get_live_psx_web(self, ticker):
        """Scrape live quote from PSX website"""
        try:
            # PSX website API endpoint for live quotes
            url = f"https://www.psx.com.pk/scripts/communicator.php?f=livequote&symbol={ticker}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and 'price' in data:
                    return {
                        'Ticker': ticker,
                        'Price': float(data.get('price', 0)),
                        'Volume': int(data.get('volume', 0)),
                        'Change': float(data.get('change', 0)),
                        'ChangePercent': float(data.get('change_percent', 0)),
                        'Open': float(data.get('open', 0)),
                        'High': float(data.get('high', 0)),
                        'Low': float(data.get('low', 0)),
                        'PreviousClose': float(data.get('prev_close', 0)),
                        'timestamp': datetime.now(),
                        'source': 'psx-web-live'
                    }

            # Alternative: PSX market summary page
            url2 = "https://www.psx.com.pk/scripts/communicator.php?f=market_summary"
            resp2 = requests.get(url2, headers=headers, timeout=10)
            if resp2.status_code == 200:
                data = resp2.json()
                for item in data.get('data', []):
                    if item.get('symbol') == ticker:
                        return {
                            'Ticker': ticker,
                            'Price': float(item.get('ldcp', 0)),
                            'Volume': int(item.get('volume', 0)),
                            'Change': float(item.get('change', 0)),
                            'ChangePercent': float(item.get('change_percent', 0)),
                            'Open': float(item.get('open', 0)),
                            'High': float(item.get('high', 0)),
                            'Low': float(item.get('low', 0)),
                            'PreviousClose': float(item.get('ycp', 0)),
                            'timestamp': datetime.now(),
                            'source': 'psx-web-live'
                        }
        except Exception as e:
            logger.error(f"PSX web scrape error for {ticker}: {e}")
        return None

    # ========== SOURCE 3: yfinance (Backup with .KA suffix) ==========
    def _get_live_yfinance(self, ticker):
        if not YFINANCE_AVAILABLE:
            return None
        try:
            # PSX stocks on Yahoo Finance use .KA suffix
            yf_ticker = f"{ticker}.KA"
            stock = yf.Ticker(yf_ticker)
            info = stock.info
            if info and 'regularMarketPrice' in info:
                return {
                    'Ticker': ticker,
                    'Price': float(info.get('regularMarketPrice', 0)),
                    'Volume': int(info.get('regularMarketVolume', 0)),
                    'Change': float(info.get('regularMarketChange', 0)),
                    'ChangePercent': float(info.get('regularMarketChangePercent', 0)),
                    'Open': float(info.get('regularMarketOpen', 0)),
                    'High': float(info.get('regularMarketDayHigh', 0)),
                    'Low': float(info.get('regularMarketDayLow', 0)),
                    'PreviousClose': float(info.get('regularMarketPreviousClose', 0)),
                    'timestamp': datetime.now(),
                    'source': 'yfinance-live'
                }
        except Exception as e:
            logger.error(f"yfinance live error for {ticker}: {e}")
        return None

    def _get_hist_yfinance(self, ticker, years=HISTORY_YEARS):
        if not YFINANCE_AVAILABLE:
            return None
        try:
            yf_ticker = f"{ticker}.KA"
            stock = yf.Ticker(yf_ticker)
            df = stock.history(period=f"{years}y")
            if df is not None and not df.empty:
                df.columns = [c.replace('Stock ', '').capitalize() for c in df.columns]
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                df.index = pd.to_datetime(df.index)
                return df
        except Exception as e:
            logger.error(f"yfinance hist error for {ticker}: {e}")
        return None

    # ========== PUBLIC METHODS ==========
    def get_live_quote(self, ticker):
        """Get real-time quote from best available source"""
        # Try cache first
        if self._is_cache_valid(ticker) and ticker in self.cache:
            return self.cache[ticker]

        quote = None

        # Try psxdata first (most reliable for PSX)
        if PSXDATA_AVAILABLE:
            quote = self._get_live_psxdata(ticker)
            if quote:
                logger.info(f"Live quote for {ticker} from psxdata: Rs. {quote['Price']}")

        # Try PSX web scraping
        if not quote:
            quote = self._get_live_psx_web(ticker)
            if quote:
                logger.info(f"Live quote for {ticker} from PSX web: Rs. {quote['Price']}")

        # Try yfinance
        if not quote:
            quote = self._get_live_yfinance(ticker)
            if quote:
                logger.info(f"Live quote for {ticker} from yfinance: Rs. {quote['Price']}")

        if quote:
            self.cache[ticker] = quote
            self.cache_time[ticker] = datetime.now()
            self.data_source = quote.get('source', 'unknown')
        else:
            logger.warning(f"NO live data available for {ticker} from any source!")

        return quote

    def get_historical(self, ticker, years=HISTORY_YEARS):
        """Get historical OHLCV from best available source"""
        cache_file = os.path.join(DATA_DIR, f"{ticker}_hist.csv")

        # Check local CSV cache first
        if os.path.exists(cache_file):
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
            if file_age.days < HIST_CACHE_DAYS:
                logger.info(f"Cache hit: {ticker}")
                try:
                    df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    if not df.empty:
                        self.data_source = 'local-cache'
                        return df
                except Exception as e:
                    logger.warning(f"Cache read failed for {ticker}: {e}")

        df = None

        # Try psxdata
        if PSXDATA_AVAILABLE:
            df = self._get_hist_psxdata(ticker, years)
            if df is not None:
                logger.info(f"Historical data for {ticker} from psxdata: {len(df)} rows")

        # Try yfinance
        if df is None and YFINANCE_AVAILABLE:
            df = self._get_hist_yfinance(ticker, years)
            if df is not None:
                logger.info(f"Historical data for {ticker} from yfinance: {len(df)} rows")

        if df is not None and not df.empty:
            df.to_csv(cache_file)
            self.data_source = 'downloaded'
            return df
        else:
            logger.error(f"NO historical data available for {ticker} from any source!")
            self.data_source = 'none'
            return None

    def get_full_data(self, ticker):
        """Historical + live merged"""
        hist = self.get_historical(ticker)
        if hist is None or hist.empty:
            return None

        live = self.get_live_quote(ticker)
        if live:
            today = pd.Timestamp.now().normalize()
            if today in hist.index:
                hist.loc[today, 'Close'] = live['Price']
                if 'Volume' in hist.columns and live['Volume']:
                    hist.loc[today, 'Volume'] = live['Volume']
                if 'High' in hist.columns:
                    hist.loc[today, 'High'] = max(hist.loc[today, 'High'], live['High'])
                if 'Low' in hist.columns:
                    hist.loc[today, 'Low'] = min(hist.loc[today, 'Low'], live['Low'])
            else:
                new_row_data = {'Close': live['Price']}
                if 'Open' in hist.columns:
                    new_row_data['Open'] = live['Open']
                if 'High' in hist.columns:
                    new_row_data['High'] = live['High']
                if 'Low' in hist.columns:
                    new_row_data['Low'] = live['Low']
                if 'Volume' in hist.columns:
                    new_row_data['Volume'] = live['Volume']

                new_row = pd.DataFrame(new_row_data, index=[today])
                hist = pd.concat([hist, new_row])
                hist = hist[~hist.index.duplicated(keep='last')]
                hist.sort_index(inplace=True)

        return hist

    def get_watchlist_live(self, watchlist=None):
        if watchlist is None:
            watchlist = WATCHLIST

        data = []
        for ticker in watchlist:
            quote = self.get_live_quote(ticker)
            if quote:
                data.append(quote)
        return pd.DataFrame(data)

    def get_kse100_index(self):
        """Get KSE-100 data"""
        return self.get_historical("KSE100", years=1)

    def get_data_source_info(self):
        """Return current data source for UI display"""
        sources = {
            'psxdata-live': ('PSX Data (Live)', 'green'),
            'psx-web-live': ('PSX Website (Live)', 'green'),
            'yfinance-live': ('Yahoo Finance (Live)', 'orange'),
            'local-cache': ('Local Cache', 'blue'),
            'downloaded': ('Downloaded', 'blue'),
            'none': ('NO DATA SOURCE', 'red'),
            'unknown': ('Unknown', 'gray')
        }
        return sources.get(self.data_source, ('Unknown', 'gray'))
