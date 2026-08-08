"""
PSX Data Feed - Direct from PSX website via psxdata
No Excel, No PC required, Cloud compatible
"""

import psxdata
import pandas as pd
from datetime import datetime, timedelta
import os
import logging

# ------------------------------------------------------------------
# Import config (fallback defaults if config.py is missing or incomplete)
# ------------------------------------------------------------------
try:
    from config import *
except ImportError:
    pass

# Ensure all config variables exist with safe defaults
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


class PSXDataFeed:
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = timedelta(minutes=LIVE_CACHE_MINUTES)
    
    def _is_cache_valid(self, ticker):
        if ticker not in self.cache_time:
            return False
        age = datetime.now() - self.cache_time[ticker]
        return age < self.cache_duration
    
    def get_live_quote(self, ticker):
        """Get real-time quote from PSX"""
        try:
            # psxdata.quote() returns a DataFrame
            df = psxdata.quote(ticker)
            if df is None or df.empty:
                logger.warning(f"No live data for {ticker}")
                return None
            
            # Extract the first row
            q = df.iloc[0]
            
            # Handle various possible column names from psxdata
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
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"Error fetching live quote for {ticker}: {e}")
            return None
    
    def get_historical(self, ticker, years=HISTORY_YEARS):
        """Get historical OHLCV from PSX"""
        cache_file = os.path.join(DATA_DIR, f"{ticker}_hist.csv")
        
        # Check local CSV cache first
        if os.path.exists(cache_file):
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
            if file_age.days < HIST_CACHE_DAYS:
                logger.info(f"Cache hit: {ticker}")
                try:
                    df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    if not df.empty:
                        return df
                except Exception as e:
                    logger.warning(f"Cache read failed for {ticker}: {e}")
        
        try:
            start_date = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            
            logger.info(f"Downloading {ticker} history from {start_date} to {end_date}...")
            
            # psxdata.stocks() returns DataFrame
            df = psxdata.stocks(ticker, start=start_date, end=end_date)
            
            if df is None or df.empty:
                logger.warning(f"No historical data returned for {ticker}")
                return None
            
            # Ensure date column is datetime and set as index
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            
            # Standardize column names
            df.columns = [c.strip().capitalize() for c in df.columns]
            
            # Keep only OHLCV columns
            ohlcv_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            available_cols = [c for c in ohlcv_cols if c in df.columns]
            if available_cols:
                df = df[available_cols]
            
            # Sort by date
            df.sort_index(inplace=True)
            
            # Save to cache
            df.to_csv(cache_file)
            logger.info(f"Saved {len(df)} rows for {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Error downloading {ticker}: {e}")
            # Fallback to cache if download fails
            if os.path.exists(cache_file):
                try:
                    return pd.read_csv(cache_file, index_col=0, parse_dates=True)
                except Exception as ce:
                    logger.error(f"Fallback cache read also failed: {ce}")
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
        """Get KSE-100 data for relative strength"""
        logger.warning("KSE-100 index OHLCV may not be available via psxdata.stocks().")
        return self.get_historical("KSE100", years=1)


# ------------------------------------------------------------------
# Quick test if run directly
# ------------------------------------------------------------------
if __name__ == "__main__":
    feed = PSXDataFeed()
    
    print("\n--- Live Quote Test ---")
    quote = feed.get_live_quote("ENGRO")
    print(quote)
    
    print("\n--- Historical Data Test ---")
    hist = feed.get_historical("ENGRO", years=1)
    if hist is not None:
        print(hist.tail())
    else:
        print("Failed to fetch historical data")