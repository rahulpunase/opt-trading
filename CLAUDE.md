# Kite Trader Platform — Claude Code Instructions

## Project overview

This is a **multi-strategy algorithmic trading platform** built on top of Zerodha's
Kite Connect API. It is not a single script — it is a plugin-based platform where
strategies are independent Python classes that can be created, configured, deployed,
started, and stopped at runtime without restarting the system.

The platform supports any strategy type: intraday options buying, positional futures,
options selling, equity delivery, spread strategies, etc. The platform doesn't know
or care what a strategy does internally — it only requires that it conforms to the
`BaseStrategy` contract.

---

## Core design principles

1. **Plugin architecture** — every strategy is a self-contained `.py` + `.yaml` pair
   dropped into the `strategies/` folder. The platform auto-discovers it.
2. **Shared infrastructure** — all strategies share one data feed (KiteTicker),
   one order router (Kite Connect), one Redis instance (namespaced per strategy),
   and one global risk gate.
3. **Runtime control** — strategies can be started, stopped, paused, and inspected
   via the FastAPI control plane without any restart.
4. **Paper trade by default** — every strategy has a `paper_trade` flag in its YAML.
   When true, orders are logged but never sent to Kite.
5. **Isolation** — strategies cannot read each other's state. Redis keys are
   namespaced as `{strategy_name}:{key}`.
6. **No hardcoded secrets** — all credentials come from `.env` via `python-dotenv`.

---

## Project structure

```
kite-trader-platform/
│
├── CLAUDE.md                        ← you are here
├── .env                             ← secrets, never committed
├── .env.example                     ← template, committed
├── .gitignore
├── .dockerignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── core/                            ← platform engine, never edit per-strategy
│   ├── __init__.py
│   ├── base_strategy.py             ← abstract base class (THE CONTRACT)
│   ├── strategy_loader.py           ← discovers & instantiates strategy plugins
│   ├── event_bus.py                 ← fans market data to all running strategies
│   ├── risk_gate.py                 ← portfolio-level risk checks
│   ├── order_router.py              ← single Kite Connect wrapper
│   ├── data_feed.py                 ← KiteTicker WebSocket + candle builder
│   └── state.py                     ← Redis wrapper, namespaced per strategy
│
├── strategies/                      ← DROP NEW STRATEGIES HERE
│   ├── intraday_options_buy.py
│   ├── intraday_options_buy.yaml
│   ├── positional_futures.py
│   ├── positional_futures.yaml
│   └── (any new strategy pair)
│
├── api/
│   ├── __init__.py
│   └── main.py                      ← FastAPI control plane + auth endpoint
│
├── dashboard/
│   └── app.py                       ← Streamlit multi-strategy P&L dashboard
│
├── alerts/
│   └── telegram.py                  ← Telegram bot notifications
│
├── logs/                            ← mounted as Docker volume
│   └── .gitkeep
│
└── trades/                          ← mounted as Docker volume
    └── .gitkeep
```

---

## The BaseStrategy contract

**Every strategy MUST subclass `BaseStrategy` and implement all abstract methods.**
Never modify `base_strategy.py` to accommodate a specific strategy — adapt the
strategy to fit the contract instead.

```python
# core/base_strategy.py
from abc import ABC, abstractmethod
from typing import Optional
import logging

class BaseStrategy(ABC):
    def __init__(self, config: dict, broker, state, logger: logging.Logger):
        self.config = config        # dict loaded from strategies/<name>.yaml
        self.broker = broker        # shared OrderRouter instance
        self.state = state          # Redis wrapper, auto-namespaced
        self.logger = logger        # per-strategy named logger
        self.name = config["name"]
        self.enabled = config.get("enabled", True)
        self.paper_trade = config.get("paper_trade", True)

    # --- REQUIRED ---

    @abstractmethod
    def on_candle(self, symbol: str, candle: dict) -> None:
        """
        Called every time a new candle closes for a subscribed symbol.
        candle = {
          "symbol": str,
          "open": float, "high": float, "low": float,
          "close": float, "volume": int,
          "timestamp": datetime
        }
        """
        ...

    @abstractmethod
    def on_tick(self, tick: dict) -> None:
        """
        Called on every live price tick for subscribed instruments.
        Use for real-time SL monitoring.
        tick = {"instrument_token": int, "last_price": float, "timestamp": datetime}
        """
        ...

    @abstractmethod
    def on_order_update(self, order: dict) -> None:
        """
        Called by the Kite postback webhook when an order status changes.
        Use to track fills, rejections, and trigger next-leg logic.
        """
        ...

    # --- OPTIONAL HOOKS (override if needed) ---

    def on_start(self) -> None:
        """Called once when the strategy is started. Use for warmup."""
        pass

    def on_stop(self) -> None:
        """Called once when the strategy is stopped. Use for cleanup."""
        pass

    def on_market_open(self) -> None:
        """Called at 9:15 AM IST every trading day."""
        pass

    def on_market_close(self) -> None:
        """Called at 3:30 PM IST — force-close any open positions here."""
        pass

    # --- BUILT-IN HELPERS (never override) ---

    def get_param(self, key: str, default=None):
        return self.config.get("params", {}).get(key, default)

    def get_instruments(self) -> list:
        return self.config.get("instruments", [])

    def get_timeframe(self) -> str:
        return self.config.get("timeframe", "5min")

    def get_capital_allocation(self) -> float:
        return self.config.get("capital_allocation", 0.10)
```

---

## Strategy YAML config schema

Every strategy has a YAML config file with the same name as its `.py` file.

```yaml
# strategies/my_strategy.yaml

name: MyStrategy               # must match class name exactly
enabled: true                  # false = loader skips it
paper_trade: true              # true = log only, no real orders

instruments:                   # list of symbols to subscribe
  - NIFTY
  - SENSEX

timeframe: 5min                # candle timeframe: 1min, 5min, 15min, daily
order_type: MIS                # MIS (intraday) | CNC (delivery) | NRML (F&O overnight)
exchange: NFO                  # NSE | BSE | NFO | BFO | MCX

capital_allocation: 0.25       # fraction of total capital for this strategy
max_trades_per_day: 4          # hard limit, enforced by the strategy itself
max_open_positions: 2

params:                        # strategy-specific, accessed via get_param()
  ema_fast: 9
  ema_slow: 21
  rsi_period: 14
  rsi_entry_long: 55
  rsi_entry_short: 45
  sl_pct: 0.35
  target1_pct: 0.50
```

---

## Core modules — what each file must do

### `core/data_feed.py`
- Connect to KiteTicker WebSocket using `api_key` and `access_token` from Redis
- Subscribe to instrument tokens for all *enabled* strategies (union of all instruments)
- Aggregate ticks into OHLCV candles for each timeframe requested by strategies
- On candle close: emit `candle_close` event to the event bus
- On every tick: emit `tick` event to the event bus
- Reconnect automatically on disconnect with exponential backoff

### `core/event_bus.py`
- Maintain a registry of running strategy instances
- On `candle_close` event: call `strategy.on_candle()` for each strategy that
  subscribes to that symbol and timeframe, using `asyncio.gather` for concurrency
- On `tick` event: call `strategy.on_tick()` for all running strategies
- Catch and log exceptions from individual strategies — one strategy crashing must
  NOT affect others
- Emit `market_open` and `market_close` events at the right IST times using APScheduler

### `core/order_router.py`
- Wrap `kiteconnect.KiteConnect` methods: `place_order`, `modify_order`,
  `cancel_order`, `get_positions`, `get_margins`
- Accept a `paper_trade: bool` flag — if true, log the intended order and return a
  fake order_id instead of calling Kite
- Rate-limit outgoing order calls to respect Kite's API limits (10 orders/sec)
- Log every order attempt (real or paper) with strategy name, timestamp, and params
- On Kite API error, retry once then alert via Telegram and return failure

### `core/risk_gate.py`
- Track portfolio-level daily P&L across all strategies combined
- Enforce: if total portfolio loss exceeds `GLOBAL_DAILY_LOSS_CAP` (from `.env`),
  call `stop()` on all strategies and block further orders
- Enforce: if total margin used exceeds `MAX_MARGIN_UTILISATION_PCT`, block new entries
- Expose `can_trade(strategy_name) -> bool` — checked by order_router before every order
- Reset daily counters at market open (9:15 AM IST)

### `core/strategy_loader.py`
- Scan `strategies/` folder for `*.py` files (exclude `__init__.py`)
- For each `.py`, find the class that subclasses `BaseStrategy`
- Load the matching `.yaml` config file (same filename, `.yaml` extension)
- Skip strategies with `enabled: false`
- Instantiate each strategy with shared broker, state, and a named logger
- Return list of instantiated strategy objects
- Support hot-reload: re-scan and load a new strategy without full restart

### `core/state.py`
- Wrap `redis.Redis` with automatic key namespacing: `{strategy_name}:{key}`
- Methods: `get`, `set`, `delete`, `hget`, `hset`, `hdel`, `hgetall`, `expire`
- Provide typed helpers: `get_int`, `get_float`, `get_json`, `set_json`
- Portfolio-level keys (not namespaced): prefix with `portfolio:`

---

## API — `api/main.py`

Build with FastAPI. All endpoints return JSON.

```
POST   /auth                     Accept request_token, exchange for access_token,
                                 store in Redis. Call this each morning.

GET    /strategies               List all strategies with status, P&L, trade count
POST   /strategy/start           Start a strategy by name (load if not loaded)
POST   /strategy/stop            Stop a strategy by name (calls on_stop())
POST   /strategy/pause           Pause signal processing (on_candle no-ops)
GET    /strategy/{name}/trades   Return today's trades for a strategy
GET    /strategy/{name}/positions Return open positions for a strategy
GET    /health                   Returns {"status": "ok"} — used by Docker healthcheck
GET    /portfolio                Aggregated P&L, margin used, daily loss vs cap
```

---

## Docker setup

### `Dockerfile`

```dockerfile
FROM python:3.11-slim

RUN useradd -m -u 1000 trader

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R trader:trader /app
USER trader

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.yml`

```yaml
version: "3.9"

services:

  trader:
    build: .
    container_name: kite_trader
    restart: unless-stopped
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
      - ./trades:/app/trades
      - ./strategies:/app/strategies   # hot-reload: add strategies without rebuild
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - trader_net

  dashboard:
    build: .
    container_name: kite_dashboard
    restart: unless-stopped
    env_file: .env
    command: ["streamlit", "run", "dashboard/app.py",
              "--server.port=8501", "--server.address=0.0.0.0"]
    ports:
      - "8501:8501"
    volumes:
      - ./trades:/app/trades
    depends_on:
      - trader
    networks:
      - trader_net

  redis:
    image: redis:7-alpine
    container_name: kite_redis
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - trader_net

volumes:
  redis_data:

networks:
  trader_net:
    driver: bridge
```

### `.dockerignore`

```
venv/
.env
__pycache__/
*.pyc
*.pyo
.git/
.gitignore
trades/*.csv
logs/*.log
*.egg-info/
.pytest_cache/
.mypy_cache/
```

### `requirements.txt`

```
kiteconnect==4.2.0
pandas==2.2.2
pandas-ta==0.3.14b
redis==5.0.4
fastapi==0.111.0
uvicorn[standard]==0.30.1
python-dotenv==1.0.1
python-telegram-bot==21.3
streamlit==1.35.0
apscheduler==3.10.4
pyyaml==6.0.1
httpx==0.27.0
pytest==8.2.2
```

---

## Environment variables — `.env`

```env
# Kite Connect
KITE_API_KEY=your_api_key_here
KITE_API_SECRET=your_api_secret_here

# Telegram alerts
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Portfolio risk
TOTAL_CAPITAL=500000
GLOBAL_DAILY_LOSS_CAP_PCT=0.03      # 3% of total capital
MAX_MARGIN_UTILISATION_PCT=0.70     # use max 70% of available margin

# Platform
PAPER_TRADE_DEFAULT=true            # overridden per strategy in YAML
LOG_LEVEL=INFO
TZ=Asia/Kolkata
```

---

## How to add a new strategy

1. Create `strategies/my_new_strategy.py` — subclass `BaseStrategy`, implement
   `on_candle`, `on_tick`, `on_order_update`
2. Create `strategies/my_new_strategy.yaml` — set name, instruments, params
3. Call `POST /strategy/start` with `{"name": "MyNewStrategy"}` — no restart needed
4. Watch logs: `docker compose logs -f trader`

The strategies folder is mounted as a volume, so new files are immediately visible
inside the running container.

---

## Coding rules for Claude Code

- All times must be in IST (`Asia/Kolkata`). Use `zoneinfo.ZoneInfo("Asia/Kolkata")`.
- Never use `time.sleep()` in strategy code — use `asyncio.sleep()`.
- Every strategy method must be wrapped in try/except. Exceptions must be logged,
  not re-raised (one bad strategy must not kill the platform).
- Never call Kite API directly from a strategy — always go through `self.broker`.
- Never read another strategy's Redis keys — use only `self.state`.
- Log every signal, order intent, fill, and exit with strategy name + timestamp.
- All order placement must check `self.paper_trade` before calling broker.
- Instrument tokens (not symbols) are what KiteTicker requires — the loader must
  resolve symbol → token using the Kite instruments CSV on startup.

---

## Daily operations

**Every morning (8:45–9:00 AM IST):**
```bash
# Get the request_token from Kite login URL, then:
curl -X POST http://localhost:8000/auth \
  -H "Content-Type: application/json" \
  -d '{"request_token": "YOUR_TOKEN_HERE"}'
```

**Start/stop a strategy:**
```bash
curl -X POST http://localhost:8000/strategy/start \
  -d '{"name": "IntradayOptionsBuy"}'

curl -X POST http://localhost:8000/strategy/stop \
  -d '{"name": "IntradayOptionsBuy"}'
```

**Check portfolio:**
```bash
curl http://localhost:8000/portfolio
```

**View logs:**
```bash
docker compose logs -f trader
```

**Deploy a new strategy without downtime:**
```bash
# 1. Drop new .py + .yaml into strategies/
# 2. Call the API — no restart
curl -X POST http://localhost:8000/strategy/start \
  -d '{"name": "MyNewStrategy"}'
```