"""
PSX Trading Engine - Streamlit Dashboard
Mobile + Desktop compatible | Cloud deploy ready

DEPLOY TO STREAMLIT CLOUD:
1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Connect your repo
4. Add secrets in Settings (GROK_API_KEY, TELEGRAM_BOT_TOKEN, etc.)
5. Done! Access from mobile/computer anywhere
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from data_feed import PSXDataFeed
from indicators import TechnicalIndicators
from stock_screener import StockScreener
from signal_engine import SignalEngine
from grok_analyzer import GrokAnalyzer
from telegram_bot import PSXTelegramBot
from news_analyzer import NewsAnalyzer
from portfolio_manager import PortfolioManager
from config import WATCHLIST, GROK_API_KEY, TELEGRAM_BOT_TOKEN, NEWS_API_KEY

st.set_page_config(
    page_title="PSX Trading Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for mobile responsiveness
st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: bold; }
    .metric-card { background: #1e1e1e; padding: 15px; border-radius: 10px; }
    @media (max-width: 768px) {
        .main-header { font-size: 1.5rem; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize components
@st.cache_resource
def get_components():
    return {
        'feed': PSXDataFeed(),
        'ind': TechnicalIndicators(),
        'screener': StockScreener(),
        'engine': SignalEngine(),
        'grok': GrokAnalyzer(),
        'telegram': PSXTelegramBot(),
        'news': NewsAnalyzer(),
        'portfolio': PortfolioManager()
    }

comps = get_components()

# Sidebar
st.sidebar.header("⚙️ Settings")
selected_ticker = st.sidebar.selectbox("Select Stock", WATCHLIST)
refresh = st.sidebar.button("🔄 Refresh Data")
run_screener = st.sidebar.button("🔍 Run Screener")

# API Status in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🔌 API Status")
st.sidebar.write(f"Grok 4.5: {'✅' if GROK_API_KEY else '❌'}")
st.sidebar.write(f"Telegram: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}")
st.sidebar.write(f"News API: {'✅' if NEWS_API_KEY else '❌'}")

if not GROK_API_KEY:
    st.sidebar.info("💡 Get Grok API: https://x.ai/api")
if not TELEGRAM_BOT_TOKEN:
    st.sidebar.info("💡 Create bot: @BotFather on Telegram")
if not NEWS_API_KEY:
    st.sidebar.info("💡 Get News API: https://newsapi.org/register")

# Main Header
st.markdown('<p class="main-header">📈 PSX Trading Engine</p>', unsafe_allow_html=True)
st.markdown("**Bloomberg-style Analysis for Pakistan Stock Exchange | Mobile + Desktop**")

# Tabs
(tab1, tab2, tab3, tab4, tab5, tab6) = st.tabs([
    "📊 Stock Analysis", "🔍 Screener", "📈 Charts", 
    "💼 Portfolio", "📰 News & Sentiment", "⚙️ Setup Guide"
])

# ========== TAB 1: Stock Analysis ==========
with tab1:
    col1, col2, col3 = st.columns(3)

    with st.spinner(f"Loading {selected_ticker}..."):
        df = comps['feed'].get_full_data(selected_ticker)

        if df is not None:
            enriched = comps['ind'].compute_all(df)
            signal, error = comps['engine'].generate_signal(selected_ticker, df)

            # News check for buy signals
            news_data = None
            if signal and "BUY" in signal['signal']:
                with st.spinner("Checking news before buy..."):
                    approved, news_data = comps['news'].check_before_buy(selected_ticker)
                    if not approved:
                        st.warning("⚠️ News check BLOCKED this buy signal. Risk detected!")

            # Grok AI
            grok_result = None
            if st.sidebar.checkbox("🤖 Enable Grok AI"):
                with st.spinner("Grok 4.5 analyzing..."):
                    grok_result, _ = comps['grok'].analyze_stock(selected_ticker, signal or {})

            latest = enriched.iloc[-1]
            with col1:
                change = latest.get('ChangePercent', 0)
                st.metric("Price", f"Rs. {latest['Close']:.2f}", f"{change:.2f}%")
            with col2:
                st.metric("RSI", f"{latest['RSI']:.1f}")
            with col3:
                score = signal['score_pct'] if signal else 0
                st.metric("Signal Score", f"{score}/100")

            # Signal Card
            if signal:
                if "BUY" in signal['signal']:
                    color = "#2e7d32"
                elif "SELL" in signal['signal']:
                    color = "#c62828"
                else:
                    color = "#616161"

                st.markdown(f"""
                <div style='padding:20px;border-radius:10px;background-color:{color};color:white;margin:10px 0;'>
                    <h2 style='margin:0;'>{signal['action']}</h2>
                    <p>Target: Rs. {signal['target']} | Stop: Rs. {signal['stop_loss']} | R/R: {signal['rr_ratio']}</p>
                    <p>News Sentiment: {signal.get('news_sentiment', 0):.2f} | News Rec: {signal.get('news_recommendation', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)

                # Action buttons
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("📱 Send to Telegram"):
                        comps['telegram'].send_sync(signal, grok_result, news_data)
                        st.success("Alert sent!")
                with c2:
                    if "BUY" in signal['signal'] and st.button("💼 Add to Portfolio"):
                        success = comps['portfolio'].add_position(
                            selected_ticker, signal['price'],
                            stop_loss=signal['stop_loss'],
                            target=signal['target'],
                            signal_data=signal
                        )
                        if success:
                            st.success(f"Added {selected_ticker} to portfolio!")
                        else:
                            st.error("Failed to add (maybe already holding or insufficient cash)")
                with c3:
                    if st.button("📰 Check News"):
                        articles = comps['news'].get_company_news(selected_ticker)
                        if articles:
                            st.write(f"Found {len(articles)} articles")
                            for a in articles[:3]:
                                st.write(f"- [{a.get('title')}]({a.get('url')})")
                        else:
                            st.info("No recent news found")

            # Grok Analysis
            if grok_result:
                with st.expander("🤖 Grok 4.5 AI Analysis"):
                    st.write(f"**Trend:** {grok_result.get('trend', 'N/A')}")
                    st.write(f"**Confidence:** {grok_result.get('confidence', 'N/A')}/10")
                    st.write(f"**Reason:** {grok_result.get('reason', 'N/A')}")
                    st.write(f"**Risk:** {grok_result.get('risk', 'N/A')}")
                    st.write(f"**Entry:** {grok_result.get('entry', 'N/A')}")
                    st.write(f"**Stop:** {grok_result.get('stop', 'N/A')}")
                    st.write(f"**Target:** {grok_result.get('target', 'N/A')}")

            # News Analysis
            if news_data:
                with st.expander("📰 News Analysis"):
                    sentiment = news_data.get('sentiment', 0)
                    st.write(f"**Sentiment Score:** {sentiment:.2f} ({'Positive' if sentiment > 0.3 else 'Negative' if sentiment < -0.3 else 'Neutral'})")
                    st.write(f"**Summary:** {news_data.get('summary', 'N/A')}")
                    st.write(f"**Recommendation:** {news_data.get('recommendation', 'N/A')}")
                    st.write(f"**Risk Flags:** {', '.join(news_data.get('risk_flags', [])) or 'None'}")

            # Score Breakdown
            if signal and signal.get('score_breakdown'):
                with st.expander("📊 Score Breakdown"):
                    for ind, score in signal['score_breakdown'].items():
                        st.progress(score / 20, text=f"{ind}: {score}/20")

# ========== TAB 2: Screener ==========
with tab2:
    if run_screener:
        with st.spinner("Screening all stocks..."):
            results = comps['screener'].screen_watchlist(WATCHLIST, comps['feed'], comps['ind'])

            if not results.empty:
                qualified = results[results['Qualified'] == True]

                st.subheader(f"✅ Qualified Stocks: {len(qualified)}")
                st.dataframe(qualified[['Ticker', 'Price', 'Score', 'RSI', 'MACD_Signal', 'SuperTrend']], use_container_width=True)

                st.subheader(f"❌ Rejected: {len(results) - len(qualified)}")
                st.dataframe(results[results['Qualified'] == False][['Ticker', 'Price', 'Score']], use_container_width=True)
            else:
                st.warning("No data available")
    else:
        st.info("Click '🔍 Run Screener' in sidebar to screen all stocks")

# ========== TAB 3: Charts ==========
with tab3:
    if df is not None:
        import plotly.graph_objects as go

        fig = go.Figure(data=[go.Candlestick(
            x=enriched.index,
            open=enriched['Open'],
            high=enriched['High'],
            low=enriched['Low'],
            close=enriched['Close'],
            name='Price'
        )])

        fig.add_trace(go.Scatter(x=enriched.index, y=enriched['SMA_20'], name='SMA 20', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=enriched.index, y=enriched['SMA_50'], name='SMA 50', line=dict(color='orange')))
        fig.add_trace(go.Scatter(x=enriched.index, y=enriched['BB_Upper'], name='BB Upper', line=dict(color='gray', dash='dash')))
        fig.add_trace(go.Scatter(x=enriched.index, y=enriched['BB_Lower'], name='BB Lower', line=dict(color='gray', dash='dash')))

        fig.update_layout(
            title=f"{selected_ticker} Price Chart",
            xaxis_rangeslider_visible=False,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        # Volume chart
        st.subheader("Volume")
        vol_df = enriched[['Volume', 'Vol_SMA20']].dropna()
        st.bar_chart(vol_df)

        # RSI chart
        st.subheader("RSI")
        rsi_df = enriched[['RSI']].dropna()
        st.line_chart(rsi_df)
    else:
        st.warning("No data available for charts")

# ========== TAB 4: Portfolio ==========
with tab4:
    st.subheader("💼 Your Portfolio")

    portfolio = comps['portfolio']
    positions = portfolio.get_positions()
    summary = portfolio.get_portfolio_summary()

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Cash", f"Rs. {summary['cash']:,.0f}")
    with c2:
        st.metric("Positions", summary['positions_count'])
    with c3:
        st.metric("Total Trades", summary['total_trades'])
    with c4:
        st.metric("Win Rate", f"{summary['winning_trades']}/{summary['total_trades']}" if summary['total_trades'] > 0 else "N/A")

    # Active positions
    if positions:
        st.subheader("📊 Active Positions")
        pos_data = []
        for pos in positions:
            # Get current price
            quote = comps['feed'].get_live_quote(pos['ticker'])
            current = quote['Price'] if quote else pos['entry_price']
            pnl = (current - pos['entry_price']) * pos['shares']
            pnl_pct = ((current - pos['entry_price']) / pos['entry_price']) * 100

            pos_data.append({
                'Ticker': pos['ticker'],
                'Entry': pos['entry_price'],
                'Current': current,
                'Shares': pos['shares'],
                'Stop Loss': pos['stop_loss'],
                'Target': pos['target'],
                'P&L': f"Rs. {pnl:,.0f}",
                'P&L %': f"{pnl_pct:+.1f}%"
            })

        st.dataframe(pd.DataFrame(pos_data), use_container_width=True)

        # Manual sell
        st.subheader("🔴 Manual Sell")
        sell_ticker = st.selectbox("Select to sell", [p['ticker'] for p in positions])
        if st.button("Sell Now"):
            quote = comps['feed'].get_live_quote(sell_ticker)
            if quote:
                record = portfolio.close_position(sell_ticker, quote['Price'], "MANUAL")
                if record:
                    st.success(f"Sold {sell_ticker}! P&L: Rs. {record['pnl']:,.2f}")
                    comps['telegram'].send_portfolio_sync(record)
    else:
        st.info("No active positions. Buy signals will auto-add here.")

    # Trade history
    history = portfolio.positions.get('history', [])
    if history:
        st.subheader("📜 Trade History")
        hist_df = pd.DataFrame(history[-20:])  # Last 20 trades
        st.dataframe(hist_df, use_container_width=True)

# ========== TAB 5: News & Sentiment ==========
with tab5:
    st.subheader("📰 Market News & Sentiment")

    # Market sentiment
    if st.button("🌍 Check Market Sentiment"):
        with st.spinner("Analyzing international news..."):
            sentiment = comps['news'].get_market_sentiment()
            st.write(f"**Sentiment Score:** {sentiment.get('sentiment', 0):.2f}")
            st.write(f"**Risk Level:** {sentiment.get('risk_level', 'N/A')}")
            st.write(f"**Summary:** {sentiment.get('summary', 'N/A')}")
            st.write(f"**Key Factors:** {', '.join(sentiment.get('key_factors', []))}")

    # Company news
    st.subheader(f"📰 News for {selected_ticker}")
    if st.button("Fetch News"):
        with st.spinner("Fetching news..."):
            articles = comps['news'].get_company_news(selected_ticker)
            if articles:
                for a in articles[:5]:
                    st.markdown(f"""
                    **{a.get('title', 'No title')}**
                    > {a.get('description', 'No description')}
                    [Read more]({a.get('url', '#')})
                    *Source: {a.get('source', {}).get('name', 'Unknown')} | {a.get('publishedAt', '')[:10]}*
                    ---
                    """)

                # AI Analysis
                with st.spinner("Grok analyzing news..."):
                    analysis = comps['news'].analyze_news_with_grok(selected_ticker, articles)
                    st.write(f"**AI Sentiment:** {analysis.get('sentiment', 0):.2f}")
                    st.write(f"**AI Summary:** {analysis.get('summary', 'N/A')}")
                    st.write(f"**AI Recommendation:** {analysis.get('recommendation', 'N/A')}")
                    st.write(f"**Risk Flags:** {', '.join(analysis.get('risk_flags', [])) or 'None'}")
            else:
                st.info("No recent news found. Check NewsAPI key in config.")

# ========== TAB 6: Setup Guide ==========
with tab6:
    st.subheader("🔧 Complete Setup Guide")

    st.markdown("""
    ### 1. Grok 4.5 API (x.ai)
    - Visit: https://x.ai/api
    - Sign up and get API key
    - Set environment variable: `GROK_API_KEY=your_key`

    ### 2. Telegram Bot
    - Message **@BotFather** on Telegram
    - Send `/newbot` and follow steps
    - Copy the **token** (looks like `123456789:ABC...`)
    - Message **@userinfobot** to get your **Chat ID**
    - Set env vars:
      ```
      TELEGRAM_BOT_TOKEN=your_token
      TELEGRAM_CHAT_ID=your_chat_id
      ```

    ### 3. News API
    - Visit: https://newsapi.org/register
    - Get free API key (100 requests/day)
    - Set env var: `NEWS_API_KEY=your_key`

    ### 4. Deploy to Streamlit Cloud
    - Push code to GitHub
    - Go to https://share.streamlit.io
    - Connect repo
    - Add secrets in Settings
    - Access from mobile/computer anywhere!

    ### 5. Environment Variables (Windows)
    Open CMD as Admin:
    ```
    setx GROK_API_KEY "your_key"
    setx TELEGRAM_BOT_TOKEN "your_token"
    setx TELEGRAM_CHAT_ID "your_chat_id"
    setx NEWS_API_KEY "your_key"
    ```
    Then restart your terminal/IDE.
    """)

    st.subheader("📱 Mobile Access")
    st.markdown("""
    Once deployed to Streamlit Cloud:
    - Open the URL on your phone browser
    - Add to home screen for app-like experience
    - Works on iOS Safari and Android Chrome
    - Telegram notifications work on all devices
    """)

st.markdown("---")
st.caption("PSX Trading Engine v2.0 | Grok 4.5 + News AI + Portfolio | Use at your own risk")
