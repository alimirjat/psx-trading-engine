"""
Comprehensive Technical Indicators
Pure Pandas - No TA-Lib dependency issues
"""

import pandas as pd
import numpy as np
from config import INDICATORS


class TechnicalIndicators:
    def __init__(self):
        self.cfg = INDICATORS

    # ========== TREND ==========
    def sma(self, df, period):
        return df['Close'].rolling(window=period).mean()

    def ema(self, df, period):
        return df['Close'].ewm(span=period, adjust=False).mean()

    def wma(self, df, period):
        weights = np.arange(1, period + 1)
        return df['Close'].rolling(window=period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True)

    # ========== MOMENTUM ==========
    def rsi(self, df, period=None):
        if period is None:
            period = self.cfg.get('RSI_PERIOD', 14)
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def macd(self, df):
        fast = self.cfg.get('MACD_FAST', 12)
        slow = self.cfg.get('MACD_SLOW', 26)
        signal = self.cfg.get('MACD_SIGNAL', 9)
        ema_fast = self.ema(df, fast)
        ema_slow = self.ema(df, slow)
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def stochastic(self, df, k_period=14, d_period=3):
        low_min = df['Low'].rolling(window=k_period).min()
        high_max = df['High'].rolling(window=k_period).max()
        k = 100 * ((df['Close'] - low_min) / (high_max - low_min))
        d = k.rolling(window=d_period).mean()
        return k, d

    def cci(self, df, period=None):
        if period is None:
            period = self.cfg.get('CCI_PERIOD', 20)   # <-- FIXED: safe get with default
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        sma_tp = tp.rolling(window=period).mean()
        mean_dev = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        # Avoid division by zero
        result = (tp - sma_tp) / (0.015 * mean_dev.replace(0, np.nan))
        return result

    def williams_r(self, df, period=14):
        highest_high = df['High'].rolling(window=period).max()
        lowest_low = df['Low'].rolling(window=period).min()
        return -100 * (highest_high - df['Close']) / (highest_high - lowest_low)

    # ========== TREND STRENGTH ==========
    def adx(self, df, period=None):
        if period is None:
            period = self.cfg.get('ADX_PERIOD', 14)

        plus_dm = df['High'].diff()
        minus_dm = df['Low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        minus_dm = abs(minus_dm)

        tr1 = df['High'] - df['Low']
        tr2 = abs(df['High'] - df['Close'].shift())
        tr3 = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr.replace(0, np.nan))
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr.replace(0, np.nan))
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.rolling(window=period).mean()

        return adx, plus_di, minus_di

    # ========== VOLATILITY ==========
    def bollinger_bands(self, df):
        period = self.cfg.get('BB_PERIOD', 20)
        std_dev = self.cfg.get('BB_STD', 2)
        sma = self.sma(df, period)
        std = df['Close'].rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        bandwidth = (upper - lower) / sma.replace(0, np.nan)
        percent_b = (df['Close'] - lower) / (upper - lower).replace(0, np.nan)
        return upper, sma, lower, bandwidth, percent_b

    def atr(self, df, period=None):
        if period is None:
            period = self.cfg.get('ATR_PERIOD', 14)
        hl = df['High'] - df['Low']
        hc = np.abs(df['High'] - df['Close'].shift())
        lc = np.abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def supertrend(self, df):
        period = self.cfg.get('SUPERTREND_PERIOD', 10)
        multiplier = self.cfg.get('SUPERTREND_MULTIPLIER', 3)
        atr = self.atr(df, period)
        hl2 = (df['High'] + df['Low']) / 2

        upper = hl2 + (multiplier * atr)
        lower = hl2 - (multiplier * atr)

        st = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)

        for i in range(len(df)):
            if i == 0:
                st.iloc[i] = upper.iloc[i]
                direction.iloc[i] = 1
                continue
            if df['Close'].iloc[i] > st.iloc[i-1]:
                direction.iloc[i] = 1
                st.iloc[i] = max(lower.iloc[i], st.iloc[i-1])
            else:
                direction.iloc[i] = -1
                st.iloc[i] = min(upper.iloc[i], st.iloc[i-1])

        return st, direction

    def keltner_channels(self, df, period=20, multiplier=2):
        ema = self.ema(df, period)
        atr = self.atr(df, period)
        upper = ema + (multiplier * atr)
        lower = ema - (multiplier * atr)
        return upper, ema, lower

    # ========== VOLUME ==========
    def obv(self, df):
        obv = pd.Series(index=df.index, dtype=float)
        obv.iloc[0] = df['Volume'].iloc[0]
        for i in range(1, len(df)):
            if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + df['Volume'].iloc[i]
            elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - df['Volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        return obv

    def vwap(self, df):
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        return (tp * df['Volume']).cumsum() / df['Volume'].cumsum()

    def mfi(self, df, period=None):
        if period is None:
            period = self.cfg.get('MFI_PERIOD', 14)
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        raw_money_flow = tp * df['Volume']

        diff = tp.diff()
        positive_flow = pd.Series(np.where(diff > 0, raw_money_flow, 0), index=df.index)
        negative_flow = pd.Series(np.where(diff < 0, raw_money_flow, 0), index=df.index)

        positive_sum = positive_flow.rolling(window=period).sum()
        negative_sum = negative_flow.rolling(window=period).sum()

        money_ratio = positive_sum / negative_sum.replace(0, np.nan)
        return 100 - (100 / (1 + money_ratio))

    def volume_sma(self, df, period=20):
        return df['Volume'].rolling(window=period).mean()

    # ========== FIBONACCI ==========
    def fibonacci_retracement(self, df, lookback=60):
        recent = df.tail(lookback)
        high = recent['High'].max()
        low = recent['Low'].min()
        diff = high - low
        return {
            '0%': high,
            '23.6%': high - 0.236 * diff,
            '38.2%': high - 0.382 * diff,
            '50%': high - 0.5 * diff,
            '61.8%': high - 0.618 * diff,
            '78.6%': high - 0.786 * diff,
            '100%': low
        }

    # ========== RELATIVE STRENGTH ==========
    def relative_strength(self, stock_df, index_df):
        stock_return = stock_df['Close'].pct_change(20)
        index_return = index_df['Close'].pct_change(20)
        rs = (stock_return + 1).cumsum() / (index_return + 1).cumsum()
        return rs * 100

    # ========== CANDLESTICK PATTERNS ==========
    def detect_patterns(self, df):
        patterns = {}

        body = abs(df['Close'] - df['Open'])
        range_total = df['High'] - df['Low']
        range_total = range_total.replace(0, np.nan)
        patterns['Doji'] = (body / range_total) < 0.1

        lower_shadow = df[['Open', 'Close']].min(axis=1) - df['Low']
        upper_shadow = df['High'] - df[['Open', 'Close']].max(axis=1)
        patterns['Hammer'] = (lower_shadow > 2 * body) & (upper_shadow < body)

        bullish_engulf = (df['Close'] > df['Open']) & (df['Open'].shift(1) > df['Close'].shift(1)) &                          (df['Open'] < df['Close'].shift(1)) & (df['Close'] > df['Open'].shift(1))
        patterns['Bullish_Engulfing'] = bullish_engulf

        return pd.DataFrame(patterns)

    # ========== COMPUTE ALL ==========
    def compute_all(self, df):
        result = df.copy()

        # Trend
        for p in self.cfg.get('SMA', [20, 50, 200]):
            result[f'SMA_{p}'] = self.sma(result, p)
        for p in self.cfg.get('EMA', [12, 26]):
            result[f'EMA_{p}'] = self.ema(result, p)
        result['WMA_20'] = self.wma(result, 20)

        # Momentum
        result['RSI'] = self.rsi(result)
        result['MACD'], result['MACD_Signal'], result['MACD_Hist'] = self.macd(result)
        result['Stoch_K'], result['Stoch_D'] = self.stochastic(result)
        result['CCI'] = self.cci(result)
        result['Williams_R'] = self.williams_r(result)

        # Trend Strength
        result['ADX'], result['Plus_DI'], result['Minus_DI'] = self.adx(result)

        # Volatility
        result['BB_Upper'], result['BB_Middle'], result['BB_Lower'], result['BB_Width'], result['BB_PercentB'] = self.bollinger_bands(result)
        result['ATR'] = self.atr(result)
        result['SuperTrend'], result['SuperTrend_Dir'] = self.supertrend(result)
        result['KC_Upper'], result['KC_Middle'], result['KC_Lower'] = self.keltner_channels(result)

        # Volume
        result['OBV'] = self.obv(result)
        result['VWAP'] = self.vwap(result)
        result['MFI'] = self.mfi(result)
        result['Vol_SMA20'] = self.volume_sma(result, 20)

        # Patterns
        patterns = self.detect_patterns(result)
        for col in patterns.columns:
            result[col] = patterns[col]

        return result
