"""
Signal Engine - Weighted scoring + Risk management + News confirmation
"""

import pandas as pd
from config import SIGNAL_CONFIG


class SignalEngine:
    def __init__(self):
        self.cfg = SIGNAL_CONFIG

    def calculate_score(self, df):
        """Calculate weighted signal score (0-100)"""
        if len(df) < 50:
            return None, "Insufficient data"

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        scores = {}

        # 1. RSI (15 points)
        rsi = latest.get('RSI')
        if pd.isna(rsi):
            scores['RSI'] = 7
        elif rsi < 30:
            scores['RSI'] = 15
        elif rsi > 70:
            scores['RSI'] = 0
        elif rsi < 50:
            scores['RSI'] = 12
        else:
            scores['RSI'] = 8

        # 2. MACD (15 points)
        macd = latest.get('MACD')
        macd_sig = latest.get('MACD_Signal')
        macd_hist = latest.get('MACD_Hist')
        prev_hist = prev.get('MACD_Hist', 0)

        if pd.isna(macd):
            scores['MACD'] = 7
        elif macd > macd_sig and prev_hist <= 0 and macd_hist > 0:
            scores['MACD'] = 15
        elif macd > macd_sig:
            scores['MACD'] = 10
        elif macd < macd_sig and prev_hist >= 0 and macd_hist < 0:
            scores['MACD'] = 0
        else:
            scores['MACD'] = 5

        # 3. SuperTrend (15 points)
        st_dir = latest.get('SuperTrend_Dir')
        if pd.isna(st_dir):
            scores['SuperTrend'] = 7
        elif st_dir == 1:
            scores['SuperTrend'] = 15
        else:
            scores['SuperTrend'] = 0

        # 4. SMA (15 points)
        sma20 = latest.get('SMA_20')
        sma50 = latest.get('SMA_50')
        price = latest['Close']

        if pd.isna(sma20) or pd.isna(sma50):
            scores['SMA'] = 7
        elif price > sma20 > sma50:
            scores['SMA'] = 15
        elif price > sma20:
            scores['SMA'] = 10
        elif price < sma20 < sma50:
            scores['SMA'] = 0
        else:
            scores['SMA'] = 5

        # 5. Bollinger (10 points)
        bb_lower = latest.get('BB_Lower')
        bb_upper = latest.get('BB_Upper')
        if pd.isna(bb_upper):
            scores['BB'] = 5
        elif price <= bb_lower:
            scores['BB'] = 10
        elif price >= bb_upper:
            scores['BB'] = 0
        else:
            scores['BB'] = 5

        # 6. Volume (10 points)
        vol = latest['Volume']
        vol_sma = latest.get('Vol_SMA20', 0)
        if pd.isna(vol_sma) or vol_sma == 0:
            scores['Volume'] = 5
        elif vol > vol_sma * self.cfg['MIN_VOLUME_RATIO']:
            scores['Volume'] = 10
        elif vol > vol_sma:
            scores['Volume'] = 7
        else:
            scores['Volume'] = 3

        # 7. VWAP (10 points)
        vwap = latest.get('VWAP')
        if pd.isna(vwap):
            scores['VWAP'] = 5
        elif price > vwap:
            scores['VWAP'] = 10
        else:
            scores['VWAP'] = 0

        # 8. ADX (10 points)
        adx = latest.get('ADX')
        if pd.isna(adx):
            scores['ADX'] = 5
        elif adx > 25:
            scores['ADX'] = 10
        elif adx > 20:
            scores['ADX'] = 7
        else:
            scores['ADX'] = 3

        total = sum(scores.values())
        pct = (total / 100) * 100

        return {
            'total_score': total,
            'breakdown': scores,
            'percentage': pct
        }, None

    def generate_signal(self, ticker, df, grok_analysis=None, news_analysis=None):
        """Generate complete trading signal with news confirmation"""
        from indicators import TechnicalIndicators
        ind = TechnicalIndicators()
        enriched = ind.compute_all(df)

        score_result, error = self.calculate_score(enriched)
        if error:
            return None, error

        score = score_result['total_score']
        pct = score_result['percentage']
        latest = enriched.iloc[-1]

        # Determine signal
        if pct >= self.cfg['STRONG_BUY_MIN']:
            signal = "STRONG_BUY"
            action = "🟢 STRONG BUY"
        elif pct >= self.cfg['BUY_MIN']:
            signal = "BUY"
            action = "🟢 BUY"
        elif pct >= self.cfg['HOLD_MIN']:
            signal = "HOLD"
            action = "⚪ HOLD"
        elif pct >= self.cfg['SELL_MIN']:
            signal = "SELL"
            action = "🔴 SELL"
        else:
            signal = "STRONG_SELL"
            action = "🔴 STRONG SELL"

        # Calculate targets using ATR
        atr = latest.get('ATR', latest['Close'] * 0.02)
        price = latest['Close']

        if "BUY" in signal:
            target = price + (atr * 3)
            stop = price - (atr * 2)
        elif "SELL" in signal:
            target = price - (atr * 3)
            stop = price + (atr * 2)
        else:
            target = price * 1.05
            stop = price * 0.95

        risk = abs(price - stop)
        reward = abs(target - price)
        rr = reward / risk if risk > 0 else 0

        # Override with Grok if available
        grok_entry = grok_analysis.get('entry') if grok_analysis else None
        grok_stop = grok_analysis.get('stop') if grok_analysis else None
        grok_target = grok_analysis.get('target') if grok_analysis else None

        # News-based adjustment
        news_sentiment = 0
        news_recommendation = "HOLD"
        if news_analysis:
            news_sentiment = news_analysis.get('sentiment', 0)
            news_recommendation = news_analysis.get('recommendation', 'HOLD')

            # Downgrade signal if news is bad
            if news_sentiment < -0.3 or news_recommendation == "AVOID":
                if "BUY" in signal:
                    signal = "HOLD"
                    action = "⚪ HOLD (News Risk)"
                elif signal == "HOLD":
                    signal = "SELL"
                    action = "🔴 SELL (News Risk)"

        result = {
            'ticker': ticker,
            'price': round(price, 2),
            'signal': signal,
            'action': action,
            'score': score,
            'score_pct': round(pct, 1),
            'score_breakdown': score_result['breakdown'],
            'target': round(target, 2),
            'stop_loss': round(stop, 2),
            'rr_ratio': round(rr, 2),
            'atr': round(atr, 2),
            'rsi': round(latest['RSI'], 2) if not pd.isna(latest.get('RSI')) else None,
            'macd_signal': "Bullish" if latest.get('MACD', 0) > latest.get('MACD_Signal', 0) else "Bearish",
            'supertrend': "Buy" if latest.get('SuperTrend_Dir') == 1 else "Sell",
            'adx': round(latest['ADX'], 2) if not pd.isna(latest.get('ADX')) else None,
            'volume_ratio': round(latest['Volume'] / latest['Vol_SMA20'], 2) if latest.get('Vol_SMA20', 0) > 0 else 0,
            'bb_position': round(latest.get('BB_PercentB', 0.5), 2),
            'grok_entry': grok_entry,
            'grok_stop': grok_stop,
            'grok_target': grok_target,
            'news_sentiment': news_sentiment,
            'news_recommendation': news_recommendation,
            'timestamp': pd.Timestamp.now()
        }

        return result, None
