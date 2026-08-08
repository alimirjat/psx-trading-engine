"""
News Analyzer - Company news + Market sentiment + War/International news
Checks news before buying via AI API
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from config import NEWS_API_KEY, NEWS_API_URL, GROK_API_KEY, GROK_API_URL, GROK_MODEL

logger = logging.getLogger(__name__)


class NewsAnalyzer:
    def __init__(self):
        self.news_api_key = NEWS_API_KEY
        self.grok_key = GROK_API_KEY

    def get_company_news(self, ticker, days_back=3):
        """Fetch recent news about a specific company"""
        if not self.news_api_key:
            logger.warning("NewsAPI key not set. Skipping news check.")
            return []

        # Map tickers to company names for better search
        company_names = {
            "ENGRO": "Engro Corporation",
            "LUCK": "Lucky Cement",
            "HBL": "Habib Bank",
            "OGDC": "Oil and Gas Development Company",
            "PSO": "Pakistan State Oil",
            "UBL": "United Bank Limited",
            "MCB": "MCB Bank",
            "EFERT": "Engro Fertilizers",
            "TRG": "TRG Pakistan",
            "SYS": "Systems Limited",
            "NETSOL": "Netsol Technologies",
            "PAEL": "Pak Elektron",
            "POWER": "Power Cement",
            "NRL": "National Refinery",
            "FFC": "Fauji Fertilizer",
            "MARI": "Mari Petroleum",
            "HASCOL": "Hascol Petroleum",
            "MLCF": "Maple Leaf Cement",
            "HUBC": "Hub Power Company",
            "ATRL": "Attock Refinery",
            "UNITY": "Unity Foods",
            "PPL": "Pakistan Petroleum",
            "DCL": "Dewan Cement",
        }

        company = company_names.get(ticker, ticker)
        query = f"{company} OR {ticker} Pakistan stock PSX"

        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        try:
            params = {
                "q": query,
                "from": from_date,
                "sortBy": "relevancy",
                "language": "en",
                "pageSize": 10,
                "apiKey": self.news_api_key
            }
            resp = requests.get(NEWS_API_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "ok":
                articles = data.get("articles", [])
                return articles
            return []
        except Exception as e:
            logger.error(f"News fetch error for {ticker}: {e}")
            return []

    def get_market_news(self, days_back=2):
        """Fetch international/war/market news affecting PSX"""
        if not self.news_api_key:
            return []

        queries = [
            "Pakistan stock market KSE-100",
            "IMF Pakistan economy",
            "oil price Pakistan",
            "USD PKR exchange rate",
            "Pakistan political news",
        ]

        all_articles = []
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        for query in queries:
            try:
                params = {
                    "q": query,
                    "from": from_date,
                    "sortBy": "relevancy",
                    "language": "en",
                    "pageSize": 5,
                    "apiKey": self.news_api_key
                }
                resp = requests.get(NEWS_API_URL, params=params, timeout=15)
                data = resp.json()
                if data.get("status") == "ok":
                    all_articles.extend(data.get("articles", []))
            except Exception as e:
                logger.error(f"Market news error for '{query}': {e}")

        # Remove duplicates by URL
        seen = set()
        unique = []
        for a in all_articles:
            url = a.get("url", "")
            if url and url not in seen:
                seen.add(url)
                unique.append(a)
        return unique[:15]

    def analyze_news_with_grok(self, ticker, articles):
        """Send news to Grok AI for sentiment analysis"""
        if not self.grok_key or not articles:
            return {"sentiment": 0, "summary": "No news analysis available", "risk_flags": []}

        # Build news text
        news_text = "\n".join([
            f"- {a.get('title', '')}: {a.get('description', '')}"
            for a in articles[:5]
        ])

        prompt = f"""Analyze these news articles about {ticker} for PSX trading:

NEWS ARTICLES:
{news_text}

Provide analysis in this EXACT format:
SENTIMENT: [number between -1.0 and 1.0 where -1=very negative, 0=neutral, 1=very positive]
SUMMARY: [2-3 sentences in Urdu/Sindhi mix explaining impact]
RISK_FLAGS: [comma separated list like "political unrest, oil price drop, IMF delay"]
RECOMMENDATION: [BUY / HOLD / AVOID]
CONFIDENCE: [1-10]
"""

        try:
            headers = {
                "Authorization": f"Bearer {self.grok_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": GROK_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a PSX stock market analyst. Be concise and factual."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 400
            }
            resp = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]

            return self._parse_news_analysis(text)
        except Exception as e:
            logger.error(f"Grok news analysis error: {e}")
            return {"sentiment": 0, "summary": "Analysis failed", "risk_flags": [], "recommendation": "HOLD", "confidence": 5}

    def _parse_news_analysis(self, text):
        """Parse Grok's news analysis response"""
        result = {
            "sentiment": 0,
            "summary": "",
            "risk_flags": [],
            "recommendation": "HOLD",
            "confidence": 5
        }

        for line in text.strip().split("\n"):
            line = line.strip()
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip().upper()
            val = val.strip()

            if key == "SENTIMENT":
                try:
                    result["sentiment"] = float(val)
                except:
                    pass
            elif key == "SUMMARY":
                result["summary"] = val
            elif key == "RISK_FLAGS":
                result["risk_flags"] = [f.strip() for f in val.split(",") if f.strip()]
            elif key == "RECOMMENDATION":
                result["recommendation"] = val.upper()
            elif key == "CONFIDENCE":
                try:
                    result["confidence"] = int(val.split("/")[0])
                except:
                    pass

        return result

    def get_market_sentiment(self):
        """Get overall market sentiment from international/war/news"""
        articles = self.get_market_news(days_back=2)
        if not articles or not self.grok_key:
            return {"sentiment": 0, "summary": "No data", "risk_level": "MEDIUM"}

        news_text = "\n".join([
            f"- {a.get('title', '')}"
            for a in articles[:8]
        ])

        prompt = f"""Analyze these latest news headlines for Pakistan Stock Exchange (PSX) market sentiment:

HEADLINES:
{news_text}

Provide in EXACT format:
SENTIMENT: [-1.0 to 1.0]
RISK_LEVEL: [LOW/MEDIUM/HIGH/CRITICAL]
SUMMARY: [one sentence in Urdu/Sindhi about market outlook]
KEY_FACTORS: [comma separated factors affecting market]
"""

        try:
            headers = {
                "Authorization": f"Bearer {self.grok_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": GROK_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a global market analyst focusing on Pakistan."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 300
            }
            resp = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=30)
            text = resp.json()["choices"][0]["message"]["content"]

            result = {"sentiment": 0, "summary": "", "risk_level": "MEDIUM", "key_factors": []}
            for line in text.strip().split("\n"):
                if ":" not in line:
                    continue
                key, val = line.split(":", 1)
                key = key.strip().upper()
                val = val.strip()

                if key == "SENTIMENT":
                    try:
                        result["sentiment"] = float(val)
                    except:
                        pass
                elif key == "RISK_LEVEL":
                    result["risk_level"] = val.upper()
                elif key == "SUMMARY":
                    result["summary"] = val
                elif key == "KEY_FACTORS":
                    result["key_factors"] = [f.strip() for f in val.split(",") if f.strip()]

            return result
        except Exception as e:
            logger.error(f"Market sentiment error: {e}")
            return {"sentiment": 0, "summary": "Error", "risk_level": "MEDIUM", "key_factors": []}

    def check_before_buy(self, ticker):
        """Complete pre-buy news check. Returns (approved: bool, analysis: dict)"""
        logger.info(f" Checking news before buying {ticker}...")

        articles = self.get_company_news(ticker)
        if not articles:
            logger.info(f"No news found for {ticker}, proceeding with caution")
            return True, {"sentiment": 0, "summary": "Koi khabar nahi mili", "risk_flags": []}

        analysis = self.analyze_news_with_grok(ticker, articles)

        sentiment = analysis.get("sentiment", 0)
        recommendation = analysis.get("recommendation", "HOLD")
        risk_flags = analysis.get("risk_flags", [])

        # Auto-reject conditions
        if sentiment < -0.5 or recommendation == "AVOID":
            logger.warning(f" News BLOCKED buy for {ticker}: sentiment={sentiment}, rec={recommendation}")
            return False, analysis

        if "bankruptcy" in str(risk_flags).lower() or "fraud" in str(risk_flags).lower() or "scam" in str(risk_flags).lower():
            logger.warning(f" Critical risk flagged for {ticker}: {risk_flags}")
            return False, analysis

        logger.info(f" News approved for {ticker}: sentiment={sentiment}")
        return True, analysis
