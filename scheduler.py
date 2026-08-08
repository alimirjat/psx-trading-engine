"""
FINAL SCHEDULER
- Dashboard: Every 1 minute (all stocks analysis)
- Telegram: Only score >= 75 (STRONG signals) + portfolio alerts
- Full Analysis: Every 5 minutes
- Daily Summary: 4 PM
- News Check: Every 10 minutes
- Portfolio monitoring: Continuous
"""

import schedule
import time
import threading
from datetime import datetime
from data_feed import PSXDataFeed
from indicators import TechnicalIndicators
from stock_screener import StockScreener
from signal_engine import SignalEngine
from grok_analyzer import GrokAnalyzer
from telegram_bot import PSXTelegramBot
from news_analyzer import NewsAnalyzer
from portfolio_manager import PortfolioManager
from config import *

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinalScheduler:
    def __init__(self):
        self.feed = PSXDataFeed()
        self.ind = TechnicalIndicators()
        self.screener = StockScreener()
        self.engine = SignalEngine()
        self.grok = GrokAnalyzer()
        self.telegram = PSXTelegramBot()
        self.news = NewsAnalyzer()
        self.portfolio = PortfolioManager()

        self.price_cache = {}
        self.signal_cache = {}
        self.dashboard_data = {}
        self.entry_zones = {}
        self.market_sentiment = {}

    def pre_calculate_zones(self):
        """Run once at startup"""
        logger.info(" Calculating entry zones...")
        for ticker in WATCHLIST:
            df = self.feed.get_full_data(ticker)
            if df is not None:
                latest = df.iloc[-1]
                atr = latest.get('ATR', latest['Close'] * 0.02)
                self.entry_zones[ticker] = {
                    'buy_zone_min': latest['Close'] - (atr * 2),
                    'buy_zone_max': latest['Close'] - (atr * 0.5),
                    'stop_loss': latest['Close'] - (atr * 2.5),
                    'target': latest['Close'] + (atr * 3)
                }

    # ========== EVERY 30 SECONDS ==========
    def price_hit_monitor(self):
        """Lightweight — price checks + portfolio monitoring"""
        for ticker in WATCHLIST:
            try:
                quote = self.feed.get_live_quote(ticker)
                if not quote:
                    continue

                price = quote['Price']
                zones = self.entry_zones.get(ticker)

                # Portfolio exit check
                pos = self.portfolio.get_position(ticker)
                if pos:
                    atr = zones.get('atr', price * 0.02) if zones else price * 0.02
                    should_close, reason, record = self.portfolio.check_exits(ticker, price, atr)
                    if should_close and record:
                        self.telegram.send_portfolio_sync(record)
                        logger.warning(f" Portfolio exit: {ticker} @ {price} | Reason: {reason}")
                    continue

                if not zones:
                    continue

                # Stop Loss Hit — ALWAYS ALERT
                if price <= zones['stop_loss']:
                    self.telegram.send_sync({
                        'ticker': ticker,
                        'action': ' STOP LOSS HIT',
                        'price': price,
                        'target': zones['target'],
                        'stop_loss': zones['stop_loss'],
                        'rr_ratio': 0,
                        'score_pct': 0,
                        'timestamp': datetime.now()
                    })
                    logger.warning(f" Stop loss hit: {ticker} @ {price}")

                # Target Hit — ALWAYS ALERT
                elif price >= zones['target']:
                    self.telegram.send_sync({
                        'ticker': ticker,
                        'action': ' TARGET HIT',
                        'price': price,
                        'target': zones['target'],
                        'stop_loss': zones['stop_loss'],
                        'rr_ratio': 0,
                        'score_pct': 0,
                        'timestamp': datetime.now()
                    })
                    logger.info(f" Target hit: {ticker} @ {price}")

                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Price monitor error {ticker}: {e}")

    # ========== EVERY 1 MINUTE ==========
    def dashboard_update(self):
        """FULL analysis for ALL stocks + news check for strong signals"""
        logger.info(" Updating dashboard data (1-min cycle)...")

        for ticker in WATCHLIST:
            try:
                df = self.feed.get_full_data(ticker)
                if df is None:
                    continue

                enriched = self.ind.compute_all(df)

                # Check if we already hold this stock
                pos = self.portfolio.get_position(ticker)

                # Generate signal
                signal, error = self.engine.generate_signal(ticker, df)

                # Store for dashboard
                self.dashboard_data[ticker] = {
                    'df': enriched,
                    'signal': signal,
                    'timestamp': datetime.now()
                }

                if signal:
                    curr_score = signal['score_pct']
                    prev_score = self.signal_cache.get(ticker, 0)
                    self.signal_cache[ticker] = curr_score

                    # STRONG SIGNAL DETECTED
                    if curr_score >= TELEGRAM_ALERT_MIN_SCORE and prev_score < TELEGRAM_ALERT_MIN_SCORE:
                        logger.info(f" STRONG SIGNAL: {ticker} score {curr_score}")

                        # Check news before confirming BUY
                        news_data = None
                        grok_data = None

                        if "BUY" in signal['signal'] and SIGNAL_CONFIG.get('NEWS_CHECK_BEFORE_BUY', True):
                            approved, news_data = self.news.check_before_buy(ticker)
                            if not approved:
                                logger.warning(f" News blocked {ticker} buy signal")
                                signal['action'] += " (News Blocked)"
                                signal['signal'] = "HOLD"
                                self.dashboard_data[ticker]['signal'] = signal
                                continue

                        # Grok AI analysis
                        market_ctx = {
                            'kse100_trend': self.market_sentiment.get('trend', 'N/A'),
                            'risk_level': self.market_sentiment.get('risk_level', 'N/A')
                        }
                        grok_data, _ = self.grok.analyze_stock(ticker, signal, market_ctx)

                        # Auto-add to portfolio if STRONG_BUY and news approved
                        if signal['signal'] == "STRONG_BUY" and not pos:
                            self.portfolio.add_position(
                                ticker=ticker,
                                entry_price=signal['price'],
                                stop_loss=signal['stop_loss'],
                                target=signal['target'],
                                signal_data=signal
                            )

                        # Send Telegram
                        self.telegram.send_sync(signal, grok_data, news_data)
                        logger.info(f" Telegram alert sent: {ticker}")

                    # SELL signal for existing positions
                    elif "SELL" in signal['signal'] and pos:
                        record = self.portfolio.close_position(ticker, signal['price'], "SELL_SIGNAL")
                        if record:
                            self.telegram.send_portfolio_sync(record)
                            self.telegram.send_sync(signal)

            except Exception as e:
                logger.error(f"Dashboard update error {ticker}: {e}")

        logger.info(" Dashboard data updated")

    # ========== EVERY 5 MINUTES ==========
    def deep_analysis(self):
        """Full recalculation + cache refresh + portfolio summary"""
        logger.info(" Running deep analysis (5-min cycle)...")

        # Update portfolio current prices
        for pos in self.portfolio.get_positions():
            try:
                quote = self.feed.get_live_quote(pos['ticker'])
                if quote:
                    pos['current_price'] = quote['Price']
            except:
                pass

        summary = self.portfolio.get_portfolio_summary()
        logger.info(f" Portfolio: {summary['positions_count']} positions | Cash: Rs. {summary['cash']:,.0f}")

        logger.info(" Deep analysis complete")

    # ========== EVERY 10 MINUTES ==========
    def news_and_sentiment(self):
        """Check market sentiment and international news"""
        logger.info(" Checking market sentiment and news...")

        try:
            sentiment = self.news.get_market_sentiment()
            self.market_sentiment = sentiment

            risk = sentiment.get('risk_level', 'MEDIUM')
            if risk in ['HIGH', 'CRITICAL']:
                logger.warning(f" Market risk elevated: {risk}")
                # Alert if risk is critical
                if risk == 'CRITICAL':
                    self.telegram.send_sync({
                        'ticker': 'MARKET',
                        'action': f' CRITICAL MARKET RISK: {risk}',
                        'price': 0,
                        'target': 0,
                        'stop_loss': 0,
                        'rr_ratio': 0,
                        'score_pct': 0,
                        'timestamp': datetime.now()
                    })

            logger.info(f" Market sentiment: {sentiment.get('sentiment', 0):.2f} | Risk: {risk}")
        except Exception as e:
            logger.error(f"News/sentiment error: {e}")

    # ========== DAILY AT 4 PM ==========
    def daily_summary(self):
        """Send daily market summary"""
        logger.info(" Sending daily summary...")

        buy_signals = []
        sell_signals = []
        hold_signals = []

        for ticker, data in self.dashboard_data.items():
            signal = data.get('signal')
            if signal:
                if "BUY" in signal['signal']:
                    buy_signals.append(signal)
                elif "SELL" in signal['signal']:
                    sell_signals.append(signal)
                else:
                    hold_signals.append(signal)

        buy_signals.sort(key=lambda x: x['score_pct'], reverse=True)

        summary = {
            'buy_count': len(buy_signals),
            'sell_count': len(sell_signals),
            'hold_count': len(hold_signals),
            'sentiment': self.market_sentiment.get('summary', 'N/A'),
            'risk_level': self.market_sentiment.get('risk_level', 'N/A'),
            'outlook': self.market_sentiment.get('summary', 'N/A'),
            'top_pick': buy_signals[0]['ticker'] if buy_signals else 'None'
        }

        self.telegram.send_summary_sync(summary)

        # Also send portfolio summary
        port_summary = self.portfolio.get_portfolio_summary()
        logger.info(f" Daily Summary: BUY={summary['buy_count']}, SELL={summary['sell_count']}, Portfolio P&L=Rs. {port_summary.get('unrealized_pnl', 0):,.2f}")

    # ========== RUN ==========
    def run(self):
        logger.info("=" * 60)
        logger.info(" PSX TRADING ENGINE STARTED")
        logger.info("=" * 60)
        logger.info(f"• Dashboard Update: Every {DASHBOARD_REFRESH} seconds")
        logger.info(f"• Telegram Alerts: Score >= {TELEGRAM_ALERT_MIN_SCORE}")
        logger.info(f"• Deep Analysis: Every {FULL_ANALYSIS_INTERVAL} seconds")
        logger.info(f"• News Check: Every {NEWS_CHECK_INTERVAL} seconds")
        logger.info(f"• Daily Summary: {DAILY_SUMMARY_TIME}")
        logger.info(f"• Grok API: {' Connected' if GROK_API_KEY else ' Not configured'}")
        logger.info(f"• News API: {' Connected' if NEWS_API_KEY else ' Not configured'}")
        logger.info(f"• Telegram: {' Connected' if TELEGRAM_BOT_TOKEN else ' Not configured'}")
        logger.info("=" * 60)

        self.pre_calculate_zones()

        # Schedule tasks
        schedule.every(PRICE_CHECK_INTERVAL).seconds.do(self.price_hit_monitor)
        schedule.every(DASHBOARD_REFRESH).seconds.do(self.dashboard_update)
        schedule.every(FULL_ANALYSIS_INTERVAL).seconds.do(self.deep_analysis)
        schedule.every(NEWS_CHECK_INTERVAL).seconds.do(self.news_and_sentiment)
        schedule.every().day.at(DAILY_SUMMARY_TIME).do(self.daily_summary)

        # Run immediately once
        self.dashboard_update()
        self.news_and_sentiment()

        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    scheduler = FinalScheduler()
    scheduler.run()
