"""
Portfolio Manager - Track positions, P&L, stop loss, targets
Sends sell signals and alerts
"""

import json
import os
import logging
from datetime import datetime
from config import PORTFOLIO_FILE, CAPITAL_PER_TRADE, MAX_POSITIONS

logger = logging.getLogger(__name__)


class PortfolioManager:
    def __init__(self):
        self.file = PORTFOLIO_FILE
        self.positions = self._load()

    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, "r") as f:
                    return json.load(f)
            except:
                return {"positions": [], "cash": 1000000, "history": []}
        return {"positions": [], "cash": 1000000, "history": []}

    def _save(self):
        with open(self.file, "w") as f:
            json.dump(self.positions, f, indent=2, default=str)

    def get_positions(self):
        return self.positions.get("positions", [])

    def get_position(self, ticker):
        for p in self.positions["positions"]:
            if p["ticker"] == ticker:
                return p
        return None

    def add_position(self, ticker, entry_price, shares=None, stop_loss=None, target=None, signal_data=None):
        """Add a new buy position"""
        if len(self.positions["positions"]) >= MAX_POSITIONS:
            logger.warning(f"Portfolio full ({MAX_POSITIONS} positions). Cannot add {ticker}")
            return False

        if self.get_position(ticker):
            logger.warning(f"Already holding {ticker}. Skipping.")
            return False

        if shares is None:
            shares = int(CAPITAL_PER_TRADE / entry_price)

        position = {
            "ticker": ticker,
            "entry_price": round(entry_price, 2),
            "shares": shares,
            "stop_loss": round(stop_loss, 2) if stop_loss else round(entry_price * 0.95, 2),
            "target": round(target, 2) if target else round(entry_price * 1.10, 2),
            "entry_date": datetime.now().isoformat(),
            "highest_price": entry_price,
            "status": "OPEN",
            "signal": signal_data or {}
        }

        cost = entry_price * shares
        if cost > self.positions["cash"]:
            logger.warning(f"Insufficient cash for {ticker}. Need Rs. {cost}, have Rs. {self.positions['cash']}")
            return False

        self.positions["cash"] -= cost
        self.positions["positions"].append(position)
        self._save()

        logger.info(f"✅ Bought {shares} shares of {ticker} @ Rs. {entry_price}")
        return True

    def close_position(self, ticker, exit_price, reason="SIGNAL"):
        """Close a position and record P&L"""
        pos = self.get_position(ticker)
        if not pos:
            return None

        pnl = (exit_price - pos["entry_price"]) * pos["shares"]
        pnl_pct = ((exit_price - pos["entry_price"]) / pos["entry_price"]) * 100

        trade_record = {
            "ticker": ticker,
            "entry_price": pos["entry_price"],
            "exit_price": round(exit_price, 2),
            "shares": pos["shares"],
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "entry_date": pos["entry_date"],
            "exit_date": datetime.now().isoformat(),
            "reason": reason,
            "holding_days": (datetime.now() - datetime.fromisoformat(pos["entry_date"])).days
        }

        self.positions["cash"] += exit_price * pos["shares"]
        self.positions["positions"] = [p for p in self.positions["positions"] if p["ticker"] != ticker]
        self.positions["history"].append(trade_record)
        self._save()

        logger.info(f"💰 Sold {ticker} @ Rs. {exit_price} | P&L: Rs. {pnl:.2f} ({pnl_pct:.1f}%) | Reason: {reason}")
        return trade_record

    def update_trailing_stop(self, ticker, current_price, atr=None):
        """Update trailing stop loss if price moves up"""
        pos = self.get_position(ticker)
        if not pos:
            return

        # Update highest price
        if current_price > pos.get("highest_price", pos["entry_price"]):
            pos["highest_price"] = current_price

            # Move stop loss up (trailing)
            if atr:
                new_stop = current_price - (atr * 2)
                if new_stop > pos["stop_loss"]:
                    pos["stop_loss"] = round(new_stop, 2)
                    logger.info(f"📈 Trailing stop updated for {ticker}: Rs. {pos['stop_loss']}")
                    self._save()

    def check_exits(self, ticker, current_price, atr=None):
        """Check if position should be closed. Returns (should_close, reason, trade_record)"""
        pos = self.get_position(ticker)
        if not pos:
            return False, None, None

        # Update trailing stop
        self.update_trailing_stop(ticker, current_price, atr)

        # Check stop loss
        if current_price <= pos["stop_loss"]:
            record = self.close_position(ticker, current_price, "STOP_LOSS")
            return True, "STOP_LOSS", record

        # Check target
        if current_price >= pos["target"]:
            record = self.close_position(ticker, current_price, "TARGET_HIT")
            return True, "TARGET_HIT", record

        return False, None, None

    def get_portfolio_summary(self):
        """Get current portfolio summary"""
        total_invested = sum(p["entry_price"] * p["shares"] for p in self.positions["positions"])
        total_value = sum(p.get("current_price", p["entry_price"]) * p["shares"] for p in self.positions["positions"])

        return {
            "cash": round(self.positions["cash"], 2),
            "positions_count": len(self.positions["positions"]),
            "total_invested": round(total_invested, 2),
            "total_value": round(total_value, 2),
            "unrealized_pnl": round(total_value - total_invested, 2),
            "total_trades": len(self.positions["history"]),
            "winning_trades": len([t for t in self.positions["history"] if t["pnl"] > 0]),
            "losing_trades": len([t for t in self.positions["history"] if t["pnl"] <= 0]),
        }

    def get_sell_recommendations(self, signals_dict):
        """Get sell recommendations based on signals"""
        sells = []
        for pos in self.positions["positions"]:
            ticker = pos["ticker"]
            signal = signals_dict.get(ticker)

            if signal and "SELL" in signal.get("signal", ""):
                sells.append({
                    "ticker": ticker,
                    "entry_price": pos["entry_price"],
                    "current_price": signal.get("price", pos["entry_price"]),
                    "signal": signal["signal"],
                    "score": signal.get("score_pct", 0),
                    "reason": "Technical SELL signal generated"
                })
        return sells
