"""
Telegram Bot — Only sends STRONG signals (score >= 75)
Plus stop loss and target hits, portfolio alerts

SETUP GUIDE:
============
1. Install: pip install python-telegram-bot==20.7
2. Message @BotFather on Telegram, create new bot, copy token
3. Message @userinfobot to get your Chat ID
4. For group: Add bot to group, then visit:
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   Look for "chat":{"id":-123456789
5. Set environment variables:
   set TELEGRAM_BOT_TOKEN=your_token
   set TELEGRAM_CHAT_ID=your_chat_id
"""

import asyncio
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ALERT_MIN_SCORE

logger = logging.getLogger(__name__)

# Graceful import — if telegram library not installed, bot works in "offline mode"
try:
    from telegram import Bot
    from telegram.constants import ParseMode
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning(" python-telegram-bot not installed!")
    logger.warning("   Run: pip install python-telegram-bot==20.7")
    logger.warning("   Telegram alerts disabled until installed.")

    # Dummy classes so code doesn't crash
    class Bot:
        def __init__(self, token):
            pass
    class ParseMode:
        HTML = "HTML"


class PSXTelegramBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.bot = Bot(token=self.token) if self.token and TELEGRAM_AVAILABLE else None

        if not TELEGRAM_AVAILABLE:
            logger.warning(" Telegram library missing. Install: pip install python-telegram-bot==20.7")
        elif not self.token:
            logger.warning(" TELEGRAM_BOT_TOKEN not set. Telegram alerts disabled.")
            logger.warning("   Setup: Message @BotFather on Telegram to create bot.")
        if not self.chat_id:
            logger.warning(" TELEGRAM_CHAT_ID not set. Telegram alerts disabled.")
            logger.warning("   Setup: Message @userinfobot to get your Chat ID.")

    async def send_signal_alert(self, signal_data, grok_data=None, news_data=None):
        """Send STRONG signal alert (score >= 75)"""
        if not self.bot or not self.chat_id or not TELEGRAM_AVAILABLE:
            return

        ticker = signal_data['ticker']
        action = signal_data['action']
        price = signal_data['price']
        target = signal_data['target']
        stop = signal_data['stop_loss']
        rr = signal_data['rr_ratio']
        score = signal_data['score_pct']

        # Only send if strong signal or stop/target hit
        is_stop_target = "STOP" in action or "TARGET" in action or "SELL" in action
        if score < TELEGRAM_ALERT_MIN_SCORE and not is_stop_target:
            return

        # Emoji based on action
        emoji = "🟢" if "BUY" in action else "" if "SELL" in action else ""
        if "STOP" in action:
            emoji = ""
        elif "TARGET" in action:
            emoji = ""

        message = f"""
{emoji} <b>{action}</b>

 <b>Stock:</b> {ticker}
 <b>Price:</b> Rs. {price}
 <b>Target:</b> Rs. {target}
 <b>Stop Loss:</b> Rs. {stop}
 <b>R/R Ratio:</b> {rr}
 <b>Confidence:</b> {score}/100

 <b>Indicators:</b>
• RSI: {signal_data.get('rsi', 'N/A')}
• MACD: {signal_data.get('macd_signal', 'N/A')}
• SuperTrend: {signal_data.get('supertrend', 'N/A')}
• ADX: {signal_data.get('adx', 'N/A')}
• Volume: {signal_data.get('volume_ratio', 'N/A')}x avg
"""

        if grok_data:
            message += f"""
 <b>Grok AI:</b>
• Trend: {grok_data.get('trend', 'N/A')}
• Confidence: {grok_data.get('confidence', 'N/A')}/10
• Risk: {grok_data.get('risk', 'N/A')}
• Reason: {grok_data.get('reason', 'N/A')}
"""

        if news_data:
            sentiment = news_data.get('sentiment', 0)
            sentiment_emoji = "🟢" if sentiment > 0.3 else "" if sentiment < -0.3 else ""
            message += f"""
 <b>News Check:</b>
• Sentiment: {sentiment_emoji} {sentiment:.2f}
• Summary: {news_data.get('summary', 'N/A')}
• Risk Flags: {', '.join(news_data.get('risk_flags', [])) or 'None'}
"""

        message += f"\n⏰ <b>Time:</b> {signal_data['timestamp'].strftime('%H:%M %d-%b-%Y')}"

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            logger.info(f" Telegram: {ticker} {action}")
        except Exception as e:
            logger.error(f" Telegram failed: {e}")

    async def send_portfolio_alert(self, trade_record):
        """Send portfolio P&L alert"""
        if not self.bot or not self.chat_id or not TELEGRAM_AVAILABLE:
            return

        pnl = trade_record.get('pnl', 0)
        pnl_pct = trade_record.get('pnl_pct', 0)
        emoji = "🟢" if pnl > 0 else ""

        message = f"""
{emoji} <b>PORTFOLIO UPDATE</b>

 <b>Stock:</b> {trade_record['ticker']}
 <b>Exit Price:</b> Rs. {trade_record['exit_price']}
 <b>Entry Price:</b> Rs. {trade_record['entry_price']}
 <b>P&L:</b> Rs. {pnl:,.2f} ({pnl_pct:+.1f}%)
 <b>Holding:</b> {trade_record.get('holding_days', 0)} days
 <b>Reason:</b> {trade_record['reason']}
"""

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Telegram portfolio alert failed: {e}")

    async def send_market_summary(self, summary_data):
        """Send daily market summary"""
        if not self.bot or not self.chat_id or not TELEGRAM_AVAILABLE:
            return

        message = f"""
 <b>DAILY MARKET SUMMARY</b>

🟢 <b>Buy Signals:</b> {summary_data.get('buy_count', 0)}
 <b>Sell Signals:</b> {summary_data.get('sell_count', 0)}
 <b>Hold:</b> {summary_data.get('hold_count', 0)}

 <b>Market Sentiment:</b> {summary_data.get('sentiment', 'N/A')}
 <b>Risk Level:</b> {summary_data.get('risk_level', 'N/A')}
 <b>Outlook:</b> {summary_data.get('outlook', 'N/A')}

 <b>Top Pick:</b> {summary_data.get('top_pick', 'None')}
"""

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Telegram summary failed: {e}")

    def send_sync(self, signal_data, grok_data=None, news_data=None):
        """Synchronous wrapper for signal alert"""
        if not TELEGRAM_AVAILABLE:
            return
        try:
            asyncio.run(self.send_signal_alert(signal_data, grok_data, news_data))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.create_task(self.send_signal_alert(signal_data, grok_data, news_data))

    def send_portfolio_sync(self, trade_record):
        """Synchronous wrapper for portfolio alert"""
        if not TELEGRAM_AVAILABLE:
            return
        try:
            asyncio.run(self.send_portfolio_alert(trade_record))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.create_task(self.send_portfolio_alert(trade_record))

    def send_summary_sync(self, summary_data):
        """Synchronous wrapper for summary"""
        if not TELEGRAM_AVAILABLE:
            return
        try:
            asyncio.run(self.send_market_summary(summary_data))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.create_task(self.send_market_summary(summary_data))
