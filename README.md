# PSX AI Trading Intelligence

Batch 01 foundation for a modular Kivy Android application.

## Current scope

- Kivy application entry point
- Android-safe configuration
- SQLite database schema
- Provider interfaces for PSX and Yahoo Finance
- Data validation contract
- Analysis engine contracts
- Intelligence engine contracts
- Grok integration boundary
- Trading decision hard-gate
- Scheduler foundation

## Deliberately NOT implemented yet

- Fake/live market values
- BUY/SELL recommendations
- Technical indicators
- Historical pattern calculations
- Financial scoring
- News scraping
- Grok API calls
- Automatic trading
- Portfolio recommendations

Those belong to later batches after the data foundation is verified.

## Run

```bash
python main.py
```

For Android:

```bash
buildozer android clean
buildozer -v android debug
```
