# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A **KDB Insights** demonstration environment integrating a FIX 4.4 market data feed with a complete time-series database stack. The stack covers real-time ingestion → stream processing → tiered storage → API-driven querying.

## Common Commands

```bash
# Start the full stack (KDB Insights + FIX feed)
docker compose up -d

# Start with a fresh build of the FIX acceptor/initiator images
docker compose up --build -d

# Full reset: stop, wipe all data, recreate dirs, restart
bash restartdb.sh

# Tail logs for specific services
docker logs -f fix-acceptor
docker logs -f fix-initiator
docker logs -f kxi-spw   # stream processor worker

# Stop everything
docker compose down
```

## Architecture

### Data Flow

```
fix-initiator
  → (FIX 4.4 TCP:5001) → fix-acceptor
  → (rtpy) → kxi-rt (Reliable Transport, topic "rawTrade")
  → kxi-spw (trade_spec.q)
      → "trade" table (all symbols)
      → "ohlc" table (AAPL only, 10-second windows)
  → kxi-da (Data Access Process, reads rdb/idb/hdb)
  → kxi-agg (Aggregator)
  → kxi-gw (Gateway: HTTP :8080, QIPC :5050)
```

### KDB Insights Services (compose.yaml)

| Service | Port | Role |
|---------|------|------|
| kxi-rc | 5040 | Resource Catalog — service discovery |
| kxi-gw | 8080/5050 | Gateway — HTTP and QIPC client endpoint |
| kxi-agg | 5060 | Aggregator — fans out queries to DAPs |
| kxi-da | 5080 | Data Access Process — reads all storage tiers |
| kxi-sm | 10001 | Storage Manager — controls rdb→idb→hdb tiering |
| kxi-rt | 5000/5002 | Reliable Transport broker |
| kxi-spc | 6000 | Stream Processor Controller |
| kxi-spw | 7000 | Stream Processor Worker (runs trade_spec.q) |
| fix-acceptor | 5001 | FIX receiver + RT publisher |

All services share the `kx` bridge network.

### Storage Tiers (config/assembly.yaml)

- **rdb** — stream mount (real-time, in kxi-rt)
- **idb** — rolled every 10 minutes to `/mnt/db/idb`
- **hdb** — daily snapshots at 01:35 AM; three retention tiers (2 days / 5 weeks / 3 months)

### FIX Feed (fix-market-feed/)

- **initiator.py** — generates randomised Quote (S) and Trade Capture (AE) messages every 2s for 5 symbols (AAPL, MSFT, GOOGL, AMZN, TSLA)
- **acceptor.py** — receives FIX messages, parses them, and publishes to RT when `RT_ENABLED=true`
  - Quotes → RT stream `"quote"` (columns: `time, sym, bid, ask, bsize, asize`)
  - Trades → RT stream `"rawTrade"` (columns: `time, sym, side, price, size`)

RT publishing requires `RT_ENABLED=true` (env var in compose.yaml), a valid `rt_client.json`, and a kdb+ licence (`KDB_LICENSE_B64` or mounted `lic/` dir).

### Stream Processor (config/src/trade_spec.q)

Reads `rawTrade` from RT and writes two tables via `.qsp.v2.write.toDatabase`:
- `trade` — every raw trade record with an added `spTime` column
- `ohlc` — 10-second timer-windowed OHLC aggregates (AAPL only)

### Custom Packages (config/packages/custom/1.0.0/)

- `da.q` — custom Data Access API registered with `.da.registerAPI`
- `agg.q` — custom Aggregator API

Hook files for lighter customisation (no package needed):
- `config/src/da/custom.q` — loaded into kxi-da via `KXI_CUSTOM_FILE`
- `config/src/agg/custom.q` — loaded into kxi-agg via `KXI_CUSTOM_FILE`

## Key Configuration

- **.env** — image versions (`kxi_db_release=1.18.0`), ports, data paths, RT tuning params
- **config/assembly.yaml** — table schemas, mount definitions, storage tier schedules
- **fix-market-feed/config/rt_client.json** — RT push/replication host (`rt-data-0:5002`) and stream name; mounted read-only into the acceptor container
- **fix-market-feed/config/acceptor.cfg / initiator.cfg** — QuickFIX session settings (FIX 4.4, TCP port 5001)

## Licence Requirement

KDB Insights images and the acceptor's RT/pykx integration require a kdb+ licence. Place licence files in `./lic/` (mounted as `/opt/kx/lic` in all KDB containers). For the acceptor, also set `QLIC=/opt/kx/lic`.
