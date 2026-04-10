# MEXC Data Sourcing Facts (Hard Validation)

## Scope

This note documents what can be sourced directly from MEXC futures feeds versus what is derived.
It is intended as a factual baseline for farmer scope decisions.

## Directly sourceable from MEXC futures APIs (official docs)

From MEXC futures websocket and market endpoint documentation:

- `push.deal` / `sub.deal`: trade stream with fields including trade price/volume/time and trade identifiers.
- `push.kline` / `sub.kline`: kline stream including interval and OHLC-related values.
- `push.depth` (and depth variants in docs): orderbook depth snapshots/updates.
- `push.ticker` / `sub.ticker`: ticker including `holdVol` (open interest), `fundingRate`, `fairPrice`, `indexPrice`.
- `push.funding.rate` / `sub.funding.rate`: funding rate stream.
- `push.index.price` / `sub.index.price`: index price stream.
- `push.fair.price` / `sub.fair.price`: fair/mark price stream.

Official sources:
- [MEXC Futures WebSocket API](https://www.mexc.com/api-docs/futures/websocket-api)
- [MEXC Futures Market Endpoints](https://www.mexc.com/api-docs/futures/market-endpoints)

## Derived-in-farmer (or downstream) vs direct

Direct from exchange feed:
- OHLC/volume/amount/trade counts (kline)
- depth ladders and best bid/ask context (depth)
- funding/index/fair prices
- open interest (`holdVol`)
- trade ticks and trade-side related flags

Derived (not single-field direct payload values):
- ratios/deltas (`spread_bps`, `imbalance`, `oi_pct_change`, `cvd_pct`, `liquidation_ratio`)
- rolling/statistical composites (`vwap`, cumulative deltas)

Conclusion:
- "all numeric features are MEXC-feed-based" is valid.
- "all numeric features are direct raw exchange scalar fields" is not valid.

## Architecture implication

- Farmer should prioritize capture + normalize + validate + audit.
- Heavy feature engineering is better placed on downstream compute (for example GPU feature services),
  while farmer keeps minimal essential derived integrity metrics.

## Notes on channel naming

- Official futures docs explicitly list `push.depth` and depth variants.
- Runtime contracts/handover may use `push.depth.full` naming in implementation context.
- Treat runtime contract naming as binding for execution, while preserving awareness of official docs naming.
