"""
Stock Screener - Qualify stocks based on multiple filters
Bloomberg-style filtering engine
"""

import pandas as pd
from config import SCREENER_CONFIG


class StockScreener:
    def __init__(self):
        self.cfg = SCREENER_CONFIG

    def qualify(self, ticker, df, kse100_df=None):
        """
        Run stock through qualification filters.
        Returns: (qualified: bool, score: int, reasons: list)
        """
        if df is None or len(df) < 50:
            return False, 0, ["Insufficient data"]

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        reasons = []
        score = 0

        # 1. Price Filter
        price = latest['Close']
        if not (self.cfg['MIN_PRICE'] <= price <= self.cfg['MAX_PRICE']):
            return False, 0, [f"Price {price} out of range"]

        # 2. Volume Filter
        volume = latest['Volume']
        vol_sma = latest.get('Vol_SMA20', 0)
        if volume < self.cfg['MIN_VOLUME']:
            return False, 0, [f"Volume too low: {volume}"]

        # 3. Trend Filters
        filters = self.cfg['TREND_FILTERS']

        # SMA Alignment
        sma20 = latest.get('SMA_20')
        sma50 = latest.get('SMA_50')
        if filters.get('sma20_above_sma50') and sma20 and sma50:
            if sma20 > sma50:
                score += 20
                reasons.append("✅ SMA20 > SMA50 (Golden alignment)")
            else:
                reasons.append("❌ SMA20 < SMA50")

        # Price above SMA20
        if filters.get('price_above_sma20') and sma20:
            if price > sma20:
                score += 15
                reasons.append("✅ Price above SMA20")
            else:
                reasons.append("❌ Price below SMA20")

        # RSI Range
        rsi = latest.get('RSI')
        if rsi and filters.get('rsi_range'):
            rsi_min, rsi_max = filters['rsi_range']
            if rsi_min <= rsi <= rsi_max:
                score += 15
                reasons.append(f"✅ RSI {rsi:.1f} in range")
            else:
                reasons.append(f"⚠️ RSI {rsi:.1f} out of range")

        # MACD Bullish
        if filters.get('macd_bullish'):
            macd = latest.get('MACD')
            macd_sig = latest.get('MACD_Signal')
            macd_hist = latest.get('MACD_Hist')
            prev_hist = prev.get('MACD_Hist', 0)

            if macd and macd_sig:
                if macd > macd_sig and macd_hist > 0 and (prev_hist is None or macd_hist > prev_hist):
                    score += 20
                    reasons.append("✅ MACD bullish crossover")
                elif macd > macd_sig:
                    score += 10
                    reasons.append("🟡 MACD above signal")
                else:
                    reasons.append("❌ MACD bearish")

        # 4. SuperTrend
        st_dir = latest.get('SuperTrend_Dir')
        if st_dir == 1:
            score += 15
            reasons.append("✅ SuperTrend BUY")
        elif st_dir == -1:
            reasons.append("❌ SuperTrend SELL")

        # 5. ADX - Trend Strength
        adx = latest.get('ADX')
        if adx and adx > 25:
            score += 10
            reasons.append(f"✅ Strong trend (ADX {adx:.1f})")

        # 6. Volume Confirmation
        if vol_sma and vol_sma > 0:
            vol_ratio = volume / vol_sma
            if vol_ratio > 1.5:
                score += 10
                reasons.append(f"✅ High volume ({vol_ratio:.1f}x avg)")
            elif vol_ratio > 1.0:
                score += 5
                reasons.append(f"🟡 Above average volume")

        # 7. Relative Strength vs KSE-100
        if kse100_df is not None and len(kse100_df) > 0:
            try:
                from indicators import TechnicalIndicators
                ind = TechnicalIndicators()
                rs = ind.relative_strength(df, kse100_df)
                latest_rs = rs.iloc[-1]
                if latest_rs > self.cfg['MIN_RS_SCORE']:
                    score += 10
                    reasons.append(f"✅ Outperforming KSE-100 (RS: {latest_rs:.1f})")
            except:
                pass

        qualified = score >= 50
        return qualified, score, reasons

    def screen_watchlist(self, watchlist, data_feed, indicators):
        """Screen entire watchlist and return qualified stocks"""
        results = []

        kse100 = data_feed.get_kse100_index()

        for ticker in watchlist:
            try:
                hist = data_feed.get_full_data(ticker)
                if hist is not None:
                    enriched = indicators.compute_all(hist)
                    qualified, score, reasons = self.qualify(ticker, enriched, kse100)

                    results.append({
                        'Ticker': ticker,
                        'Price': enriched['Close'].iloc[-1],
                        'Qualified': qualified,
                        'Score': score,
                        'RSI': enriched['RSI'].iloc[-1] if 'RSI' in enriched.columns else None,
                        'MACD_Signal': "Bullish" if enriched['MACD'].iloc[-1] > enriched['MACD_Signal'].iloc[-1] else "Bearish" if 'MACD' in enriched.columns else "N/A",
                        'SuperTrend': "Buy" if enriched['SuperTrend_Dir'].iloc[-1] == 1 else "Sell" if 'SuperTrend_Dir' in enriched.columns else "N/A",
                        'Volume_Ratio': enriched['Volume'].iloc[-1] / enriched['Vol_SMA20'].iloc[-1] if 'Vol_SMA20' in enriched.columns and enriched['Vol_SMA20'].iloc[-1] > 0 else 0,
                        'Reasons': reasons
                    })
            except Exception as e:
                results.append({
                    'Ticker': ticker,
                    'Price': 0,
                    'Qualified': False,
                    'Score': 0,
                    'RSI': None,
                    'MACD_Signal': "Error",
                    'SuperTrend': "Error",
                    'Volume_Ratio': 0,
                    'Reasons': [str(e)]
                })

        return pd.DataFrame(results)
