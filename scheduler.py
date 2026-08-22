from database import Database
from data_engine import DataEngine
from analysis_engine import AnalysisEngine
from intelligence_engine import IntelligenceEngine
from ai_engine import GrokClient, AIResearchEngine
from trading_engine import TradingEngine
from config import GROK_API_KEY, GROK_MODEL

class Scheduler:
    def __init__(self, db=None):
        self.db = db or Database()
        self.data_eng = DataEngine(self.db)
        self.analysis_eng = AnalysisEngine()
        self.intel_eng = IntelligenceEngine()
        self.ai_eng = AIResearchEngine(GrokClient(GROK_API_KEY, GROK_MODEL))
        self.trading_eng = TradingEngine()

    def run_pipeline_for_symbol(self, symbol):
        evidence = self.data_eng.collect_data(symbol)
        evidence["technical"] = self.analysis_eng.calculate_technical(
            symbol, evidence.get("historical_data"))
        evidence["fundamentals_analysis"] = self.analysis_eng.calculate_fundamentals(
            symbol, evidence.get("financials"))
        evidence["valuation"] = self.analysis_eng.calculate_valuation(
            symbol, evidence.get("financials"), evidence.get("psx"))
        evidence["historical_pattern"] = self.analysis_eng.find_historical_patterns(
            symbol, evidence.get("historical_data"))

        evidence["news"] = self.intel_eng.verify_news(symbol, evidence.get("news", []))
        evidence["industry"] = self.intel_eng.analyze_industry(symbol, {})
        evidence["macro"] = self.intel_eng.analyze_macro(symbol, {})
        evidence["geopolitics"] = self.intel_eng.analyze_geopolitics(symbol, {})
        evidence["catalysts"] = self.intel_eng.identify_catalysts(symbol, evidence)

        verification = self.intel_eng.verify_evidence(evidence)
        evidence["verification_status"] = bool(verification.get("verified", False))

        evidence["ai_research"] = self.ai_eng.research(evidence)
        evidence["ai_red_team"] = self.ai_eng.red_team(evidence)

        gate = {"verified": evidence["verification_status"]}
        evidence["decision"] = {
            "intraday": self.trading_eng.scan_intraday(gate),
            "swing": self.trading_eng.scan_swing(gate),
            "long_term": self.trading_eng.scan_longterm(gate),
            "five_x": self.trading_eng.scan_five_x(gate),
        }
        self.db.save_evidence(evidence)
        return evidence

    def run_market_scan(self):
        result = self.data_eng.psx.get_market_snapshot()
        if result.status != "OK":
            return {"status": "BLOCKED",
                    "message": "PSX live feed unavailable: " + result.message,
                    "market": None}
        return {"status": "READY",
                "message": f"PSX live feed verified • {result.data['count']} symbols received. Step-1 acquisition is complete; analysis remains gated.",
                "market": result.data}
