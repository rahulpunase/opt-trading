# Graph Report - .  (2026-04-29)

## Corpus Check
- Corpus is ~19,435 words - fits in a single context window. You may not need a graph.

## Summary
- 357 nodes · 676 edges · 45 communities detected
- Extraction: 58% EXTRACTED · 42% INFERRED · 0% AMBIGUOUS · INFERRED: 287 edges (avg confidence: 0.7)
- Token cost: 4,800 input · 2,100 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Core Platform Modules|Core Platform Modules]]
- [[_COMMUNITY_Architecture Design Spec|Architecture Design Spec]]
- [[_COMMUNITY_API & Event Processing|API & Event Processing]]
- [[_COMMUNITY_Strategy Execution Engine|Strategy Execution Engine]]
- [[_COMMUNITY_Data Feed & Alerts|Data Feed & Alerts]]
- [[_COMMUNITY_Options Straddle Strategy|Options Straddle Strategy]]
- [[_COMMUNITY_Instrument Cache|Instrument Cache]]
- [[_COMMUNITY_Risk Gate & State|Risk Gate & State]]
- [[_COMMUNITY_Strategy Loader & State|Strategy Loader & State]]
- [[_COMMUNITY_Subscription Management|Subscription Management]]
- [[_COMMUNITY_BaseStrategy Contract|BaseStrategy Contract]]
- [[_COMMUNITY_Frontend Auth Flow|Frontend Auth Flow]]
- [[_COMMUNITY_Frontend Search UI|Frontend Search UI]]
- [[_COMMUNITY_Live Quote Hooks|Live Quote Hooks]]
- [[_COMMUNITY_API Client & Dashboard|API Client & Dashboard]]
- [[_COMMUNITY_WebSocket Provider|WebSocket Provider]]
- [[_COMMUNITY_Coding Rules & Standards|Coding Rules & Standards]]
- [[_COMMUNITY_Frontend Assets|Frontend Assets]]
- [[_COMMUNITY_React App Entry|React App Entry]]
- [[_COMMUNITY_Status Badge Component|Status Badge Component]]
- [[_COMMUNITY_Layout Component|Layout Component]]
- [[_COMMUNITY_PnL Chart Component|PnL Chart Component]]
- [[_COMMUNITY_Login Page|Login Page]]
- [[_COMMUNITY_Dashboard Page|Dashboard Page]]
- [[_COMMUNITY_Trades Page|Trades Page]]
- [[_COMMUNITY_Strategies Page|Strategies Page]]
- [[_COMMUNITY_Data Analysis Deps|Data Analysis Deps]]
- [[_COMMUNITY_Streamlit Dashboard|Streamlit Dashboard]]
- [[_COMMUNITY_Frontend Docs & Assets|Frontend Docs & Assets]]
- [[_COMMUNITY_Broker Decoupling Rationale|Broker Decoupling Rationale]]
- [[_COMMUNITY_Paper Trade Rationale|Paper Trade Rationale]]
- [[_COMMUNITY_Redis Isolation Rationale|Redis Isolation Rationale]]
- [[_COMMUNITY_Core Package Init|Core Package Init]]
- [[_COMMUNITY_ESLint Config|ESLint Config]]
- [[_COMMUNITY_Vite Build Config|Vite Build Config]]
- [[_COMMUNITY_Positions Page|Positions Page]]
- [[_COMMUNITY_Symbol Page|Symbol Page]]
- [[_COMMUNITY_API Package Init|API Package Init]]
- [[_COMMUNITY_Uvicorn Dependency|Uvicorn Dependency]]
- [[_COMMUNITY_HTTPX Dependency|HTTPX Dependency]]
- [[_COMMUNITY_Pytest Dependency|Pytest Dependency]]
- [[_COMMUNITY_Debugpy Dependency|Debugpy Dependency]]
- [[_COMMUNITY_RapidFuzz Dependency|RapidFuzz Dependency]]
- [[_COMMUNITY_Frontend Icon Assets|Frontend Icon Assets]]
- [[_COMMUNITY_React Asset|React Asset]]

## God Nodes (most connected - your core abstractions)
1. `InstrumentCache` - 33 edges
2. `EventBus` - 33 edges
3. `DataFeed` - 29 edges
4. `StrategyLoader` - 28 edges
5. `OrderRouter` - 26 edges
6. `RiskGate` - 24 edges
7. `StrategyState` - 23 edges
8. `NiftyExpiryStraddle` - 20 edges
9. `BaseStrategy` - 18 edges
10. `lifespan()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `PositionalFutures` --uses--> `BaseStrategy`  [INFERRED]
  strategies/positional_futures.py → core/base_strategy.py
- `NiftyExpiryStraddle` --uses--> `BaseStrategy`  [INFERRED]
  strategies/nifty_expiry_straddle.py → core/base_strategy.py
- `IntradayOptionsBuy` --uses--> `BaseStrategy`  [INFERRED]
  strategies/intraday_options_buy.py → core/base_strategy.py
- `Multiplexed real-time tick stream. Client sends subscribe/unsubscribe JSON messa` --uses--> `RiskGate`  [INFERRED]
  api/main.py → core/risk_gate.py
- `lifespan()` --calls--> `RiskGate`  [INFERRED]
  api/main.py → core/risk_gate.py

## Hyperedges (group relationships)
- **Core Event Pipeline: data_feed -> event_bus -> strategies** — claude_data_feed, claude_event_bus, claude_basestrategy_on_candle, claude_basestrategy_on_tick, claude_basestrategy_on_market_open, claude_basestrategy_on_market_close [EXTRACTED 0.95]
- **Strategy Plugin Contract: BaseStrategy + YAML + Loader** — claude_basestrategy, claude_strategy_yaml_schema, claude_strategy_loader, claude_intraday_options_buy, claude_positional_futures [EXTRACTED 0.92]
- **Risk Management Subsystem: risk_gate + order_router + global loss cap + margin utilisation** — claude_risk_gate, claude_order_router, claude_global_daily_loss_cap, claude_max_margin_utilisation [EXTRACTED 0.90]

## Communities

### Community 0 - "Core Platform Modules"
Cohesion: 0.08
Nodes (31): BaseModel, DataFeed, InstrumentCache, Return the full instrument dict for a given token., Translate an index tradingsymbol to its F&O exchange + name.         E.g. ("NIFT, AuthRequest, _cached_instruments(), instrument_expiries() (+23 more)

### Community 1 - "Architecture Design Spec"
Cohesion: 0.06
Nodes (41): alerts/telegram.py — Telegram Bot Notifications, api/main.py — FastAPI Control Plane, BaseStrategy Abstract Contract, BaseStrategy.on_candle Abstract Method, BaseStrategy.on_market_close Hook, BaseStrategy.on_market_open Hook, BaseStrategy.on_order_update Abstract Method, BaseStrategy.on_start Hook (+33 more)

### Community 2 - "API & Event Processing"
Cohesion: 0.1
Nodes (15): Fuzzy search across tradingsymbol and name fields using rapidfuzz., Prefix search across tradingsymbols. Returns up to 50 results., auth_status(), _build_ws_payload(), get_positions(), get_trades(), instruments_search(), list_available_strategies() (+7 more)

### Community 3 - "Strategy Execution Engine"
Cohesion: 0.12
Nodes (3): BaseStrategy, IntradayOptionsBuy, PositionalFutures

### Community 4 - "Data Feed & Alerts"
Cohesion: 0.1
Nodes (10): EventBus, auth(), auth_logout(), lifespan(), telegram_test(), Called after /auth when DataFeed is started — injected into all subsequently loa, send_alert(), start_bot() (+2 more)

### Community 5 - "Options Straddle Strategy"
Cohesion: 0.19
Nodes (1): NiftyExpiryStraddle

### Community 6 - "Instrument Cache"
Cohesion: 0.11
Nodes (11): _expiry_str(), Build in-memory lookup structures and swap them in atomically., Convert Kite instrument dicts to a JSON-serialisable form., Write instruments to today's JSON cache file atomically., Group a flat instrument list by segment → name → instrument_type, sorted by expi, Reconstruct a flat instrument list from the grouped file structure., Delete instrument JSON files from previous days., Normalise expiry to ISO string regardless of whether it's a date or already a st (+3 more)

### Community 7 - "Risk Gate & State"
Cohesion: 0.18
Nodes (1): StrategyState

### Community 8 - "Strategy Loader & State"
Cohesion: 0.18
Nodes (4): Bulk-resolve a list of symbols for one exchange. Skips unknowns., make_redis_client(), Resolve the strategy's `instruments` list to Kite instrument_tokens.         Fal, StrategyLoader

### Community 9 - "Subscription Management"
Cohesion: 0.15
Nodes (7): Subscribe to an instrument beyond the YAML instruments list. Call from on_start(, Dynamically subscribe to a token. Reference-counted so multiple consumers share, Decrement refcount; unsubscribe from KiteTicker when no consumers remain., Resolve a symbol+exchange pair to an instrument_token., instruments_lookup(), Multiplexed real-time tick stream. Client sends subscribe/unsubscribe JSON messa, ws_quotes()

### Community 10 - "BaseStrategy Contract"
Cohesion: 0.17
Nodes (2): ABC, BaseStrategy

### Community 11 - "Frontend Auth Flow"
Cohesion: 0.29
Nodes (3): useAuth(), AuthCallback(), ProtectedRoute()

### Community 12 - "Frontend Search UI"
Cohesion: 0.4
Nodes (2): handleKeyDown(), handleSelect()

### Community 13 - "Live Quote Hooks"
Cohesion: 0.4
Nodes (2): useQuoteContext(), useSymbolQuote()

### Community 14 - "API Client & Dashboard"
Cohesion: 0.5
Nodes (2): request(), fetch()

### Community 15 - "WebSocket Provider"
Cohesion: 0.67
Nodes (0): 

### Community 16 - "Coding Rules & Standards"
Cohesion: 0.67
Nodes (3): Asyncio Over time.sleep Rule, Coding Rules for Claude Code, IST Timezone Enforcement Rule

### Community 17 - "Frontend Assets"
Cohesion: 0.67
Nodes (3): Platform Favicon — Lightning Bolt / Layered Stack Logo (Purple Gradient), Hero Image — Isometric Layered Stack / Platform Abstraction Diagram, Frontend Entry Point (index.html)

### Community 18 - "React App Entry"
Cohesion: 1.0
Nodes (0): 

### Community 19 - "Status Badge Component"
Cohesion: 1.0
Nodes (0): 

### Community 20 - "Layout Component"
Cohesion: 1.0
Nodes (0): 

### Community 21 - "PnL Chart Component"
Cohesion: 1.0
Nodes (0): 

### Community 22 - "Login Page"
Cohesion: 1.0
Nodes (0): 

### Community 23 - "Dashboard Page"
Cohesion: 1.0
Nodes (0): 

### Community 24 - "Trades Page"
Cohesion: 1.0
Nodes (0): 

### Community 25 - "Strategies Page"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "Data Analysis Deps"
Cohesion: 1.0
Nodes (2): pandas 2.2.2, ta 0.11.0 (Technical Analysis)

### Community 27 - "Streamlit Dashboard"
Cohesion: 1.0
Nodes (2): dashboard/app.py — Streamlit P&L Dashboard, streamlit 1.35.0

### Community 28 - "Frontend Docs & Assets"
Cohesion: 1.0
Nodes (2): Frontend README — React + TypeScript + Vite Template, Vite Logo SVG (purple lightning bolt in parentheses)

### Community 29 - "Broker Decoupling Rationale"
Cohesion: 1.0
Nodes (1): Called every time a new candle closes for a subscribed symbol.         candle =

### Community 30 - "Paper Trade Rationale"
Cohesion: 1.0
Nodes (1): Called on every live price tick for subscribed instruments.         tick = {"ins

### Community 31 - "Redis Isolation Rationale"
Cohesion: 1.0
Nodes (1): Called by the Kite postback webhook when an order status changes.

### Community 32 - "Core Package Init"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "ESLint Config"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Vite Build Config"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Positions Page"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Symbol Page"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "API Package Init"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Uvicorn Dependency"
Cohesion: 1.0
Nodes (1): uvicorn[standard] 0.30.1

### Community 39 - "HTTPX Dependency"
Cohesion: 1.0
Nodes (1): httpx 0.27.0

### Community 40 - "Pytest Dependency"
Cohesion: 1.0
Nodes (1): pytest 8.2.2

### Community 41 - "Debugpy Dependency"
Cohesion: 1.0
Nodes (1): debugpy 1.8.1

### Community 42 - "RapidFuzz Dependency"
Cohesion: 1.0
Nodes (1): rapidfuzz >=3.9.0

### Community 43 - "Frontend Icon Assets"
Cohesion: 1.0
Nodes (1): Social/UI Icons SVG Sprite (Bluesky, Discord, GitHub, X, Social, Documentation)

### Community 44 - "React Asset"
Cohesion: 1.0
Nodes (1): React Logo SVG (blue atom orbital icon)

## Knowledge Gaps
- **56 isolated node(s):** `Called every time a new candle closes for a subscribed symbol.         candle =`, `Called on every live price tick for subscribed instruments.         tick = {"ins`, `Called by the Kite postback webhook when an order status changes.`, `Subscribe to an instrument beyond the YAML instruments list. Call from on_start(`, `Normalise expiry to ISO string regardless of whether it's a date or already a st` (+51 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `React App Entry`** (2 nodes): `App.tsx`, `main.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Status Badge Component`** (2 nodes): `StatusBadge.tsx`, `StatusBadge()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Layout Component`** (2 nodes): `Layout.tsx`, `handleLogout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PnL Chart Component`** (2 nodes): `PnlChart.tsx`, `PnlChart()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Login Page`** (2 nodes): `Login.tsx`, `handleLogin()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Dashboard Page`** (2 nodes): `fmt()`, `Dashboard.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Trades Page`** (2 nodes): `Trades.tsx`, `fmt()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Strategies Page`** (2 nodes): `Strategies.tsx`, `handle()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Data Analysis Deps`** (2 nodes): `pandas 2.2.2`, `ta 0.11.0 (Technical Analysis)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Streamlit Dashboard`** (2 nodes): `dashboard/app.py — Streamlit P&L Dashboard`, `streamlit 1.35.0`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Docs & Assets`** (2 nodes): `Frontend README — React + TypeScript + Vite Template`, `Vite Logo SVG (purple lightning bolt in parentheses)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Broker Decoupling Rationale`** (1 nodes): `Called every time a new candle closes for a subscribed symbol.         candle =`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Paper Trade Rationale`** (1 nodes): `Called on every live price tick for subscribed instruments.         tick = {"ins`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Redis Isolation Rationale`** (1 nodes): `Called by the Kite postback webhook when an order status changes.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Core Package Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `ESLint Config`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Vite Build Config`** (1 nodes): `vite.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Positions Page`** (1 nodes): `Positions.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Symbol Page`** (1 nodes): `SymbolPage.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `API Package Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Uvicorn Dependency`** (1 nodes): `uvicorn[standard] 0.30.1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `HTTPX Dependency`** (1 nodes): `httpx 0.27.0`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Pytest Dependency`** (1 nodes): `pytest 8.2.2`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Debugpy Dependency`** (1 nodes): `debugpy 1.8.1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `RapidFuzz Dependency`** (1 nodes): `rapidfuzz >=3.9.0`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Icon Assets`** (1 nodes): `Social/UI Icons SVG Sprite (Bluesky, Discord, GitHub, X, Social, Documentation)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `React Asset`** (1 nodes): `React Logo SVG (blue atom orbital icon)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `lifespan()` connect `Data Feed & Alerts` to `Core Platform Modules`, `API & Event Processing`, `Strategy Execution Engine`, `Instrument Cache`, `Strategy Loader & State`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `StrategyLoader` connect `Strategy Loader & State` to `Core Platform Modules`, `Data Feed & Alerts`, `Risk Gate & State`, `Subscription Management`, `BaseStrategy Contract`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `BaseStrategy` connect `BaseStrategy Contract` to `Strategy Execution Engine`, `Data Feed & Alerts`, `Options Straddle Strategy`, `Strategy Loader & State`, `Subscription Management`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `InstrumentCache` (e.g. with `AuthRequest` and `StrategyRequest`) actually correct?**
  _`InstrumentCache` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `EventBus` (e.g. with `AuthRequest` and `StrategyRequest`) actually correct?**
  _`EventBus` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `DataFeed` (e.g. with `AuthRequest` and `StrategyRequest`) actually correct?**
  _`DataFeed` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `StrategyLoader` (e.g. with `BaseStrategy` and `StrategyState`) actually correct?**
  _`StrategyLoader` has 17 INFERRED edges - model-reasoned connections that need verification._