import sqlite3
from pathlib import Path
import json
from config import database_path


class Database:
    def __init__(self, path=None):
        self.path = Path(path) if path else database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(
            str(self.path),
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS stock_evidence (
            symbol TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            price REAL,
            volume REAL,
            financials TEXT,
            technical TEXT,
            historical_pattern TEXT,
            news TEXT,
            industry TEXT,
            macro TEXT,
            geopolitics TEXT,
            valuation TEXT,
            risk TEXT,
            catalysts TEXT,
            verification_status INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(symbol, observed_at)
        );

        CREATE TABLE IF NOT EXISTS raw_source_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            symbol TEXT,
            retrieved_at TEXT NOT NULL,
            status TEXT NOT NULL,
            payload TEXT
        );
        """)
        self.conn.commit()

    def save_evidence(self, ev):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.conn.execute("""
            INSERT OR REPLACE INTO stock_evidence
            (symbol, observed_at, price, volume, financials, technical,
             historical_pattern, news, industry, macro, geopolitics,
             valuation, risk, catalysts, verification_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ev.get("symbol"),
            now,
            ev.get("price"),
            ev.get("volume"),
            json.dumps(ev.get("financials", {})),
            json.dumps(ev.get("technical", {})),
            json.dumps(ev.get("historical_pattern", {})),
            json.dumps(ev.get("news", [])),
            json.dumps(ev.get("industry", {})),
            json.dumps(ev.get("macro", {})),
            json.dumps(ev.get("geopolitics", {})),
            json.dumps(ev.get("valuation", {})),
            json.dumps(ev.get("risk", {})),
            json.dumps(ev.get("catalysts", [])),
            1 if ev.get("verification_status") else 0,
        ))
        self.conn.commit()

    def save_raw(self, source, symbol, result):
        self.conn.execute(
            "INSERT INTO raw_source_data(source,symbol,retrieved_at,status,payload) VALUES(?,?,?,?,?)",
            (
                source,
                symbol,
                result.get("retrieved_at", ""),
                result.get("status", ""),
                json.dumps(result.get("data")),
            ),
        )
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
