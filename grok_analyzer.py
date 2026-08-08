"""
Grok AI Analyzer - Market sentiment + Technical analysis
Uses x.ai Grok 4.5 API
"""

import requests
import json
import logging
from config import GROK_API_KEY, GROK_API_URL, GROK_MODEL

logger = logging.getLogger(__name__)


class GrokAnalyzer:
    def __init__(self):
        self.api_key = GROK_API_KEY
        self.api_url = GROK_API_URL
        self.model = GROK_MODEL

    def analyze_stock(self, ticker, signal_data, market_context=None):
        """
        Send stock data to Grok AI for analysis
        Returns: dict with trend, entry, stop, target, confidence
        """
        if not self.api_key:
            return None, "Grok API key not configured. Get from https://x.ai/api"

        prompt = self._build_prompt(ticker, signal_data, market_context)

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert PSX stock analyst. Respond in concise bullet points with clear trading recommendations. Use Urdu/Sindhi mix for reasons."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            analysis = result['choices'][0]['message']['content']

            parsed = self._parse_response(analysis)
            return parsed, None

        except Exception as e:
            logger.error(f"Grok API error: {e}")
            return None, str(e)

    def _build_prompt(self, ticker, signal_data, market_context):
        """Build detailed prompt for Grok"""

        mc = market_context or {}

        prompt = f"""Analyze {ticker} for PSX trading:

TECHNICAL DATA:
- Price: Rs. {signal_data.get('price', 'N/A')}
- Signal: {signal_data.get('signal', 'N/A')} (Score: {signal_data.get('score_pct', 'N/A')}/100)
- RSI: {signal_data.get('rsi', 'N/A')}
- MACD: {signal_data.get('macd_signal', 'N/A')}
- SuperTrend: {signal_data.get('supertrend', 'N/A')}
- Volume Ratio: {signal_data.get('volume_ratio', 'N/A')}x
- ATR: {signal_data.get('atr', 'N/A')}
- Stop Loss: {signal_data.get('stop_loss', 'N/A')}
- Target: {signal_data.get('target', 'N/A')}

MARKET CONTEXT:
- KSE-100 Trend: {mc.get('kse100_trend', 'N/A')}
- USD/PKR: {mc.get('usd_pkr', 'N/A')}
- Oil Price: {mc.get('oil_price', 'N/A')}
- Global Sentiment: {mc.get('global', 'N/A')}
- Market Risk Level: {mc.get('risk_level', 'N/A')}

Provide in this EXACT format:
TREND: [Bullish/Bearish/Neutral]
CONFIDENCE: [1-10]
ENTRY: [price]
STOP: [price]
TARGET: [price]
REASON: [one sentence in Sindhi/Urdu mix]
RISK: [Low/Medium/High]
"""
        return prompt

    def _parse_response(self, text):
        """Parse structured data from Grok's text response"""
        lines = text.strip().split('\n')
        result = {}

        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().upper()
                value = value.strip()

                if key == 'TREND':
                    result['trend'] = value
                elif key == 'CONFIDENCE':
                    try:
                        result['confidence'] = int(value.split('/')[0])
                    except:
                        result['confidence'] = 5
                elif key == 'ENTRY':
                    result['entry'] = value
                elif key == 'STOP':
                    result['stop'] = value
                elif key == 'TARGET':
                    result['target'] = value
                elif key == 'REASON':
                    result['reason'] = value
                elif key == 'RISK':
                    result['risk'] = value

        return result

    def get_market_sentiment(self, news_summary=""):
        """Get overall market sentiment from Grok"""
        if not self.api_key:
            return None

        prompt = f"""Analyze PSX market sentiment based on:
- Global markets: S&P 500, Shanghai, Oil
- Local factors: USD/PKR, political stability, IMF
- Recent news: {news_summary}

Respond ONLY with:
SENTIMENT: [Bullish/Bearish/Neutral]
CONFIDENCE: [1-10]
KEY_DRIVER: [one sentence in Urdu/Sindhi]
RISK_LEVEL: [LOW/MEDIUM/HIGH/CRITICAL]
"""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a Pakistan stock market expert."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 200
            }
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            text = response.json()['choices'][0]['message']['content']

            result = {}
            for line in text.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    result[k.strip().upper()] = v.strip()
            return result
        except Exception as e:
            logger.error(f"Sentiment error: {e}")
            return None
