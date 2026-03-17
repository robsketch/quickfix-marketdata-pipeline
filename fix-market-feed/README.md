# FIX Market Data Feed

A dummy FIX 4.4 market data feed built with **QuickFIX/Python**, containerised
with Docker. The feed generates randomised **Quote (S)** and **Trade Capture
Report (AE)** messages for a set of dummy equity symbols.

---

## Architecture

```
┌─────────────────────────────────────┐     fix-net (bridge)
│  fix-initiator (container)          │
│  ─────────────────────────────────  │
│  • Generates Quote (S) messages     │──────────────────────►┐
│  • Generates Trade (AE) messages    │   FIX 4.4 / TCP:5001  │
│  • Random-walks mid prices          │                        ▼
│  • Publishes every 2 seconds        │     ┌──────────────────────────────────┐
└─────────────────────────────────────┘     │  fix-acceptor (container)        │
                                            │  ──────────────────────────────  │
                                            │  • Listens on :5001              │
                                            │  • Parses Quote & Trade msgs     │
                                            │  • Logs structured output        │
                                            │  • Ready for KDB hook            │
                                            └──────────────────────────────────┘
```

---

## Symbols

`AAPL · MSFT · GOOGL · AMZN · TSLA`

Prices random-walk from realistic base values. Spreads are 5 bps.

---

## Message Types

| Type | FIX MsgType | Fields published |
|------|-------------|-----------------|
| Quote | `S` | QuoteID, Symbol, BidPx, OfferPx, BidSize, OfferSize, TransactTime |
| Trade Capture Report | `AE` | TradeReportID, Symbol, LastPx, LastQty, Side, TransactTime |

---

## Quick Start

```bash
# Build and start both containers
docker-compose up --build

# Tail acceptor logs (parsed messages)
docker logs -f fix-acceptor

# Tail initiator logs (sent messages)
docker logs -f fix-initiator

# Stop everything
docker-compose down
```

---

## Project Layout

```
fix-market-feed/
├── acceptor/
│   ├── acceptor.py        # FIX acceptor app + message parsers
│   └── Dockerfile
├── initiator/
│   ├── initiator.py       # FIX initiator app + message generators
│   └── Dockerfile
├── config/
│   ├── acceptor.cfg       # QuickFIX session config for acceptor
│   └── initiator.cfg      # QuickFIX session config for initiator
├── logs/                  # Mounted log volumes (git-ignored)
│   ├── acceptor/
│   └── initiator/
└── docker-compose.yml
```

---

## Tuning

| Parameter | Location | Default |
|-----------|----------|---------|
| Publish interval | `initiator.py` → `PUBLISH_INTERVAL_SECS` | 2s |
| Symbols | `initiator.py` → `SYMBOLS` | 5 equities |
| Base prices | `initiator.py` → `BASE_PRICES` | Realistic USD prices |
| Price volatility | `initiator.py` → `_tick_price()` | ±0.2% per tick |
| FIX port | `docker-compose.yml` / `*.cfg` | 5001 |

---

## KDB Insights RT Integration

The acceptor publishes directly to KDB Insights Reliable Transport via `rtpy`.

| FIX Message | RT Stream | Columns |
|-------------|-----------|---------|
| Quote (S)   | `quote`   | `time, sym, bid, ask, bsize, asize` |
| Trade (AE)  | `trade`   | `time, sym, side, price, size, tradeID` |

### Setup

1. Obtain your `rt_client.json` from your KDB Insights instance (via the
   Information Service or a local RT config file).
2. Place it at `config/rt_client.json` — it is mounted read-only into the
   acceptor container at `/app/config/rt_client.json`.
3. The RT stream names (`quote`, `trade`) must match the topics configured
   in your KDB Insights assembly. Update them in `acceptor.py` if needed.
4. A valid PyKX / kdb+ licence is required to use `kx.Table` serialisation.
   Set the `KDB_LICENSE_B64` env var or mount your licence file and set
   `QLIC` accordingly in `docker-compose.yml`.

### Dependencies installed in the acceptor image

```
quickfix
pykx
kxi-rtpy  (from https://portal.dl.kx.com/assets/pypi/)
```
