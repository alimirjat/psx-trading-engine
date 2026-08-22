from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Optional
import re, requests
from config import API_TIMEOUT

PSX_MARKET_URL="https://www.psx.com.pk/market-summary/"
YAHOO_URL="https://query1.finance.yahoo.com/v8/finance/chart"

def now_utc(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

@dataclass
class DataResult:
    source:str; status:str; data:Any=None; message:str=""; retrieved_at:str=""
    def as_dict(self): return asdict(self)

class Provider:
    name="BASE"
    def __init__(self,timeout=API_TIMEOUT):
        self.timeout=timeout
        self.session=requests.Session()
        self.session.headers.update({"User-Agent":"Mozilla/5.0 PSX-AI/1.0"})
    def error(self,msg): return DataResult(self.name,"ERROR",message=str(msg),retrieved_at=now_utc())

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.tables=[]; self.table=None; self.row=None; self.cell=None; self.buf=[]
    def handle_starttag(self,tag,attrs):
        tag=tag.lower()
        if tag=="table": self.table=[]
        elif tag=="tr" and self.table is not None: self.row=[]
        elif tag in ("th","td") and self.row is not None: self.cell=tag; self.buf=[]
    def handle_data(self,data):
        if self.cell is not None: self.buf.append(data)
    def handle_endtag(self,tag):
        tag=tag.lower()
        if tag in ("th","td") and self.cell is not None:
            self.row.append(re.sub(r"\s+"," ","".join(self.buf)).strip()); self.cell=None; self.buf=[]
        elif tag=="tr" and self.row is not None:
            if any(self.row): self.table.append(self.row)
            self.row=None
        elif tag=="table" and self.table is not None:
            if self.table: self.tables.append(self.table)
            self.table=None

def num(v):
    if v is None: return None
    s=str(v).replace(",","").replace("%","").strip()
    if s in ("","-","--","N/A","NA"): return None
    try: return float(s)
    except ValueError: return None

class PSXProvider(Provider):
    name="PSX"
    def get_market_snapshot(self):
        try:
            r=self.session.get(PSX_MARKET_URL,timeout=self.timeout); r.raise_for_status()
            p=TableParser(); p.feed(r.text)
            best=None
            for t in p.tables:
                if not t: continue
                h=" ".join(x.lower() for x in t[0])
                score=sum(k in h for k in ("scrip","current","change","volume","price"))
                if score>=3 and (best is None or score>best[0]): best=(score,t)
            if not best: return self.error("PSX page reached but market table was not found.")
            headers=best[1][0]; quotes=[]
            for raw in best[1][1:]:
                row=dict(zip(headers,raw))
                symbol=row.get("SCRIP") or row.get("SYMBOL")
                if not symbol: continue
                def pick(*names):
                    for n in names:
                        if n in row: return row[n]
                quotes.append({
                    "symbol":str(symbol).strip(),
                    "ldcp":num(pick("LDCP","PREVIOUS CLOSE")),
                    "open":num(pick("OPEN")),
                    "high":num(pick("HIGH")),
                    "low":num(pick("LOW")),
                    "current":num(pick("CURRENT","PRICE")),
                    "change":num(pick("CHANGE")),
                    "change_pct":num(pick("%CHANGE","PERCENT CHANGE")),
                    "volume":num(pick("VOLUME")),
                })
            quotes=[q for q in quotes if q["symbol"]]
            if not quotes: return self.error("PSX market table contained no usable symbols.")
            return DataResult("PSX","OK",{"source_url":r.url,"retrieved_at":now_utc(),"quotes":quotes,"count":len(quotes)},retrieved_at=now_utc())
        except Exception as e: return self.error(e)
    def get_quote(self,symbol):
        r=self.get_market_snapshot()
        if r.status!="OK": return r
        for q in r.data["quotes"]:
            if q["symbol"].upper()==str(symbol).upper().strip(): return DataResult("PSX","OK",q,retrieved_at=now_utc())
        return self.error(f"{symbol} not found in PSX market table.")

class YahooProvider(Provider):
    name="Yahoo Finance"
    def get_history(self,symbol,range_="5y",interval="1d"):
        try:
            ticker=str(symbol).upper().strip()
            if not ticker.endswith(".KAR"): ticker+=".KAR"
            r=self.session.get(f"{YAHOO_URL}/{ticker}",params={"range":range_,"interval":interval,"events":"div,splits"},timeout=self.timeout)
            r.raise_for_status(); result=r.json().get("chart",{}).get("result")
            if not result: return self.error(f"No Yahoo history returned for {ticker}.")
            return DataResult("Yahoo Finance","OK",result[0],retrieved_at=now_utc())
        except Exception as e: return self.error(e)
    def get_quote(self,symbol): return self.error("Yahoo quote is secondary evidence.")

class DataValidator:
    @staticmethod
    def compare_prices(primary:Optional[float],secondary:Optional[float],tolerance=.02):
        if primary is None or secondary is None: return {"status":"INSUFFICIENT_DATA"}
        try: p,s=float(primary),float(secondary)
        except: return {"status":"INVALID_DATA"}
        d=abs(p-s); a=max(abs(p)*tolerance,.01)
        return {"status":"PASS" if d<=a else "CONFLICT","primary":p,"secondary":s,"difference":d,"allowed_difference":a}

class DataEngine:
    def __init__(self,db):
        self.db=db; self.psx=PSXProvider(); self.yahoo=YahooProvider(); self.validator=DataValidator()
    def health(self): return {"psx":"READY","yahoo":"READY","database":"READY","timestamp":now_utc()}
    def collect_symbol_history(self,symbol):
        r=self.yahoo.get_history(symbol)
        if r.status=="OK": self.db.save_raw(r.source,symbol,r.as_dict())
        return r
    def collect_data(self,symbol):
        p=self.psx.get_quote(symbol); h=self.collect_symbol_history(symbol)
        return {"symbol":str(symbol).upper(),"price":p.data.get("current") if p.status=="OK" else None,
                "volume":p.data.get("volume") if p.status=="OK" else None,"financials":{},"news":[],
                "historical_data":h.data if h.status=="OK" else None,"psx":p.as_dict(),
                "historical_source":h.as_dict(),"verification_status":False,
                "verification_reason":"" if p.status=="OK" else p.message}
