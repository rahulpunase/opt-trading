# Graph Report - /Users/macbookpro/Documents/projects/trading/opt-trading  (2026-05-03)

## Corpus Check
- 40 files · ~60,850 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 434 nodes · 933 edges · 62 communities detected
- Extraction: 46% EXTRACTED · 54% INFERRED · 0% AMBIGUOUS · INFERRED: 501 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]

## God Nodes (most connected - your core abstractions)
1. `InstrumentCache` - 58 edges
2. `EventBus` - 57 edges
3. `DataFeed` - 53 edges
4. `StrategyLoader` - 53 edges
5. `OrderRouter` - 50 edges
6. `RiskGate` - 48 edges
7. `CandleStore` - 42 edges
8. `StrategyState` - 26 edges
9. `BaseStrategy` - 25 edges
10. `lifespan()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `StrategyState` --uses--> `Called after /auth when DataFeed is started — injected into all subsequently loa`  [INFERRED]
  /Users/macbookpro/Documents/projects/trading/opt-trading/core/state.py → core/strategy_loader.py
- `StrategyState` --uses--> `Resolve the strategy's `instruments` list to Kite instrument_tokens.         Fal`  [INFERRED]
  /Users/macbookpro/Documents/projects/trading/opt-trading/core/state.py → core/strategy_loader.py
- `BaseStrategy` --uses--> `Called after /auth when DataFeed is started — injected into all subsequently loa`  [INFERRED]
  /Users/macbookpro/Documents/projects/trading/opt-trading/core/base_strategy.py → core/strategy_loader.py
- `BaseStrategy` --uses--> `Resolve the strategy's `instruments` list to Kite instrument_tokens.         Fal`  [INFERRED]
  /Users/macbookpro/Documents/projects/trading/opt-trading/core/base_strategy.py → core/strategy_loader.py
- `BaseStrategy` --uses--> `NiftyExpiryStraddle`  [INFERRED]
  /Users/macbookpro/Documents/projects/trading/opt-trading/core/base_strategy.py → strategies/nifty_expiry_straddle.py

## Hyperedges (group relationships)
- **Core Event Pipeline: data_feed -> event_bus -> strategies** — claude_data_feed, claude_event_bus, claude_basestrategy_on_candle, claude_basestrategy_on_tick, claude_basestrategy_on_market_open, claude_basestrategy_on_market_close [EXTRACTED 0.95]
- **Strategy Plugin Contract: BaseStrategy + YAML + Loader** — claude_basestrategy, claude_strategy_yaml_schema, claude_strategy_loader, claude_intraday_options_buy, claude_positional_futures [EXTRACTED 0.92]
- **Risk Management Subsystem: risk_gate + order_router + global loss cap + margin utilisation** — claude_risk_gate, claude_order_router, claude_global_daily_loss_cap, claude_max_margin_utilisation [EXTRACTED 0.90]

## Communities

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (57): BaseModel, CandleStore, DataFeed, EventBus, InstrumentCache, Return the full instrument dict for a given token., Translate an index tradingsymbol to its F&O exchange + name.         E.g. ("NIFT, Return today's JSON file path if it exists, else None. (+49 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (10): ABC, BaseStrategy, BaseStrategy, Return last n closed candles (historical + live), oldest first. Returns a list c, IntradayOptionsBuy, Intraday options buying strategy using EMA crossover + RSI confirmation.      Si, PositionalFutures, PositionalFutures — EMA crossover trend-following strategy for F&O futures.  Sig (+2 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (20): request(), fetch(), Called by DataFeed for every tick. Aggregates only into timeframes that have bee, Fuzzy search across tradingsymbol and name fields using rapidfuzz., Prefix search across tradingsymbols. Returns up to 50 results., auth_status(), _build_ws_payload(), get_positions() (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (41): alerts/telegram.py — Telegram Bot Notifications, api/main.py — FastAPI Control Plane, BaseStrategy Abstract Contract, BaseStrategy.on_candle Abstract Method, BaseStrategy.on_market_close Hook, BaseStrategy.on_market_open Hook, BaseStrategy.on_order_update Abstract Method, BaseStrategy.on_start Hook (+33 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (17): Capture the loop so ingest_tick (called from KiteTicker thread) can dispatch cor, auth(), auth_logout(), _auto_restart_strategies(), lifespan(), Load, warm up, and register a strategy. Raises on failure., Re-start any strategies recorded as running before the last shutdown., _start_strategy() (+9 more)

### Community 5 - "Community 5"
Cohesion: 0.1
Nodes (11): Subscribe to an instrument beyond the YAML instruments list. Call from on_start(, _bucket_start(), _market_open_today(), Shared OHLCV candle store with historical backfill + live aggregation.  Single s, Idempotent backfill via kite.historical_data. Returns number of candles loaded., Dynamically subscribe to a token. Reference-counted so multiple consumers share, Decrement refcount; unsubscribe from KiteTicker when no consumers remain., Resolve a symbol+exchange pair to an instrument_token. (+3 more)

### Community 6 - "Community 6"
Cohesion: 0.19
Nodes (1): NiftyExpiryStraddle

### Community 7 - "Community 7"
Cohesion: 0.15
Nodes (1): StrategyState

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (10): _expiry_str(), Build in-memory lookup structures and swap them in atomically., Convert Kite instrument dicts to a JSON-serialisable form., Write instruments to today's JSON cache file atomically., Group a flat instrument list by segment → name → instrument_type, sorted by expi, Reconstruct a flat instrument list from the grouped file structure., Delete instrument JSON files from previous days., Normalise expiry to ISO string regardless of whether it's a date or already a st (+2 more)

### Community 9 - "Community 9"
Cohesion: 0.17
Nodes (3): Bulk-resolve a list of symbols for one exchange. Skips unknowns., Translate an index tradingsymbol to its F&O exchange + name.         E.g. ("NIFT, Resolve the strategy's `instruments` list to Kite instrument_tokens.         Fal

### Community 10 - "Community 10"
Cohesion: 0.29
Nodes (3): useAuth(), AuthCallback(), ProtectedRoute()

### Community 11 - "Community 11"
Cohesion: 0.4
Nodes (2): handleKeyDown(), handleSelect()

### Community 12 - "Community 12"
Cohesion: 0.4
Nodes (2): useQuoteContext(), useSymbolQuote()

### Community 13 - "Community 13"
Cohesion: 0.67
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 0.67
Nodes (3): Asyncio Over time.sleep Rule, Coding Rules for Claude Code, IST Timezone Enforcement Rule

### Community 15 - "Community 15"
Cohesion: 0.67
Nodes (3): Platform Favicon — Lightning Bolt / Layered Stack Logo (Purple Gradient), Hero Image — Isometric Layered Stack / Platform Abstraction Diagram, Frontend Entry Point (index.html)

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (0): 

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (0): 

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (2): pandas 2.2.2, ta 0.11.0 (Technical Analysis)

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (2): dashboard/app.py — Streamlit P&L Dashboard, streamlit 1.35.0

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (2): Frontend README — React + TypeScript + Vite Template, Vite Logo SVG (purple lightning bolt in parentheses)

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Called every time a new candle closes for a subscribed symbol.         candle =

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Called on every live price tick for subscribed instruments.         tick = {"ins

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Called by the Kite postback webhook when an order status changes.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (0): 

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Return the full instrument dict for a given token.

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Fuzzy search across tradingsymbol and name fields using rapidfuzz.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Prefix search across tradingsymbols. Returns up to 50 results.

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Build in-memory lookup structures and swap them in atomically.

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Convert Kite instrument dicts to a JSON-serialisable form.

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Write instruments to today's JSON cache file atomically.

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Group a flat instrument list by segment → name → instrument_type, sorted by expi

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Reconstruct a flat instrument list from the grouped file structure.

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Delete instrument JSON files from previous days.

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Called every time a new candle closes for a subscribed symbol.         candle =

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Called on every live price tick for subscribed instruments.         tick = {"ins

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Called by the Kite postback webhook when an order status changes.

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Subscribe to an instrument beyond the YAML instruments list. Call from on_start(

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Dynamically subscribe to a token. Reference-counted so multiple consumers share

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Decrement refcount; unsubscribe from KiteTicker when no consumers remain.

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): uvicorn[standard] 0.30.1

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): httpx 0.27.0

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): pytest 8.2.2

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): debugpy 1.8.1

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): rapidfuzz >=3.9.0

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Social/UI Icons SVG Sprite (Bluesky, Discord, GitHub, X, Social, Documentation)

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): React Logo SVG (blue atom orbital icon)

## Knowledge Gaps
- **77 isolated node(s):** `Shared OHLCV candle store with historical backfill + live aggregation.  Single s`, `Capture the loop so ingest_tick (called from KiteTicker thread) can dispatch cor`, `Idempotent backfill via kite.historical_data. Returns number of candles loaded.`, `Called by DataFeed for every tick. Aggregates only into timeframes that have bee`, `Return last n closed candles (historical + live), oldest first. Returns a list c` (+72 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 16`** (2 nodes): `kite()`, `order_router.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (2 nodes): `StatusBadge()`, `StatusBadge.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (2 nodes): `handleLogout()`, `Layout.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (2 nodes): `PnlChart.tsx`, `PnlChart()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `utils.ts`, `cn()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `handleLogin()`, `Login.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (2 nodes): `fmt()`, `Dashboard.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (2 nodes): `fmt()`, `Trades.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (2 nodes): `handle()`, `Strategies.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (2 nodes): `pandas 2.2.2`, `ta 0.11.0 (Technical Analysis)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (2 nodes): `dashboard/app.py — Streamlit P&L Dashboard`, `streamlit 1.35.0`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `Frontend README — React + TypeScript + Vite Template`, `Vite Logo SVG (purple lightning bolt in parentheses)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Called every time a new candle closes for a subscribed symbol.         candle =`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Called on every live price tick for subscribed instruments.         tick = {"ins`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Called by the Kite postback webhook when an order status changes.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `vite.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `App.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `main.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `OhlcChart.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Positions.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `SymbolPage.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Return the full instrument dict for a given token.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Fuzzy search across tradingsymbol and name fields using rapidfuzz.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Prefix search across tradingsymbols. Returns up to 50 results.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Build in-memory lookup structures and swap them in atomically.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Convert Kite instrument dicts to a JSON-serialisable form.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Write instruments to today's JSON cache file atomically.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Group a flat instrument list by segment → name → instrument_type, sorted by expi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Reconstruct a flat instrument list from the grouped file structure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Delete instrument JSON files from previous days.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Called every time a new candle closes for a subscribed symbol.         candle =`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Called on every live price tick for subscribed instruments.         tick = {"ins`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Called by the Kite postback webhook when an order status changes.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Subscribe to an instrument beyond the YAML instruments list. Call from on_start(`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Dynamically subscribe to a token. Reference-counted so multiple consumers share`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Decrement refcount; unsubscribe from KiteTicker when no consumers remain.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `uvicorn[standard] 0.30.1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `httpx 0.27.0`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `pytest 8.2.2`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `debugpy 1.8.1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `rapidfuzz >=3.9.0`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Social/UI Icons SVG Sprite (Bluesky, Discord, GitHub, X, Social, Documentation)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `React Logo SVG (blue atom orbital icon)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `StrategyLoader` connect `Community 0` to `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 7`, `Community 9`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `BaseStrategy` connect `Community 1` to `Community 0`, `Community 4`, `Community 5`, `Community 6`, `Community 9`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `InstrumentCache` connect `Community 0` to `Community 2`, `Community 4`, `Community 5`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `InstrumentCache` (e.g. with `AuthRequest` and `StrategyRequest`) actually correct?**
  _`InstrumentCache` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `EventBus` (e.g. with `AuthRequest` and `StrategyRequest`) actually correct?**
  _`EventBus` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 40 inferred relationships involving `DataFeed` (e.g. with `AuthRequest` and `StrategyRequest`) actually correct?**
  _`DataFeed` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `StrategyLoader` (e.g. with `BaseStrategy` and `StrategyState`) actually correct?**
  _`StrategyLoader` has 41 INFERRED edges - model-reasoned connections that need verification._