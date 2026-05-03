import asyncio
import datetime
import heapq
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import yaml

import redis as redis_lib
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from kiteconnect import KiteConnect
from pydantic import BaseModel

from alerts.telegram import send_alert, start_bot, stop_bot
from core.data_feed import DataFeed
from core.event_bus import EventBus
from core.instrument_cache import InstrumentCache
from core.order_router import OrderRouter
from core.risk_gate import RiskGate
from core.state import make_redis_client
from core.strategy_loader import StrategyLoader

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

if os.getenv("DEBUG") == "1":
    import debugpy
    try:
        debugpy.listen(("0.0.0.0", 5678))
    except RuntimeError:
        pass  # already listening (e.g. second reload worker)
logger = logging.getLogger("api")

# Shared singletons
_redis: redis_lib.Redis = None
_kite: KiteConnect = None
_broker: OrderRouter = None
_event_bus: EventBus = None
_risk_gate: RiskGate = None
_loader: StrategyLoader = None
_running_strategies: dict = {}
_data_feed: DataFeed = None
_instrument_cache: InstrumentCache = None

# Nearest F&O expiries to return for /instruments/{token}/expiries
MAX_SYMBOL_EXPIRIES = 5

# Option chain rows: strikes within this many steps above/below ATM (inclusive of ATM → up to 51 rows)
MAX_OPTION_CHAIN_STRIKES_EACH_SIDE = 25


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _kite, _broker, _event_bus, _risk_gate, _loader, _instrument_cache, _data_feed

    _redis = make_redis_client()
    _kite = KiteConnect(api_key=os.getenv("KITE_API_KEY", ""))
    _instrument_cache = InstrumentCache(_kite)

    stored_token = _redis.get("kite:access_token")
    if stored_token:
        access_token = stored_token.decode()
        _kite.set_access_token(access_token)
        logger.info("Restored access_token from Redis")

    # Warm Redis from today's file cache on startup (survives Redis restarts without re-auth)
    if not _instrument_cache.is_cached():
        today_file = _instrument_cache.today_cache_file()
        if today_file:
            try:
                count = await asyncio.get_event_loop().run_in_executor(
                    None, _instrument_cache.fetch_and_cache
                )
                logger.info("Redis warmed from file cache on startup: %d instruments", count)
            except Exception as e:
                logger.warning("Could not warm Redis from file cache: %s", e)
        else:
            logger.info("No instrument file cache for today — will populate on first /auth or search")

    paper_default = os.getenv("PAPER_TRADE_DEFAULT", "true").lower() == "true"
    _broker = OrderRouter(_kite, paper_trade=paper_default)
    _event_bus = EventBus()
    _risk_gate = RiskGate(_redis)
    _loader = StrategyLoader(_broker, _risk_gate, _instrument_cache)
    _event_bus.start_scheduler()

    # If we already have a valid access token, start the ticker immediately
    if stored_token:
        try:
            _data_feed = DataFeed(
                api_key=os.getenv("KITE_API_KEY", ""),
                access_token=access_token,
                event_bus=_event_bus,
                instrument_tokens=[],
            )
            _data_feed.start()
            _loader.set_data_feed(_data_feed)
            logger.info("DataFeed started from restored access_token")
        except Exception as e:
            logger.warning("DataFeed could not start on startup: %s", e)

    await start_bot()
    logger.info("Platform started. No strategies auto-loaded — start them via API.")
    yield

    await stop_bot()
    for s in _running_strategies.values():
        try:
            s.on_stop()
        except Exception as e:
            logger.error("Error stopping %s: %s", s.name, e)
    _event_bus.stop_scheduler()


app = FastAPI(title="Kite Trader Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    request_token: str


class StrategyRequest(BaseModel):
    name: str


@app.get("/auth/login")
async def auth_login():
    url = f"https://kite.zerodha.com/connect/login?v=3&api_key={os.getenv('KITE_API_KEY', '')}"
    return {"login_url": url}


@app.get("/auth")
async def auth(request_token: str):
    global _data_feed
    try:
        data = _kite.generate_session(request_token, api_secret=os.getenv("KITE_API_SECRET", ""))
        access_token = data["access_token"]
        _kite.set_access_token(access_token)
        _redis.set("kite:access_token", access_token)
        logger.info("Auth successful, user=%s", data.get("user_id", "unknown"))

        # Fetch and cache all instruments — runs once per login, ~1-2s
        try:
            instruments_count = await asyncio.get_event_loop().run_in_executor(
                None, _instrument_cache.fetch_and_cache
            )
            logger.info("Instrument cache populated: %d instruments", instruments_count)
        except Exception as e:
            logger.error("Instrument cache fetch failed: %s", e)
            instruments_count = 0

        if _data_feed:
            _data_feed.stop()
        _data_feed = DataFeed(
            api_key=os.getenv("KITE_API_KEY", ""),
            access_token=access_token,
            event_bus=_event_bus,
            instrument_tokens=[],
        )
        _data_feed.start()
        _loader.set_data_feed(_data_feed)

        return {
            "status": "ok",
            "access_token": access_token,
            "user_id": data.get("user_id"),
            "user_name": data.get("user_name"),
            "instruments_cached": instruments_count,
            "login_url": f"https://kite.zerodha.com/connect/login?v=3&api_key={os.getenv('KITE_API_KEY', '')}",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/auth")
async def auth_logout():
    global _data_feed
    try:
        _kite.invalidate_access_token()
    except Exception:
        pass
    _redis.delete("kite:access_token")
    if _data_feed:
        _data_feed.stop()
        _data_feed = None
    logger.info("Logged out, access_token invalidated")
    return {"status": "logged_out"}


@app.get("/auth/status")
async def auth_status():
    try:
        profile = _kite.profile()
        return {"authenticated": True, "user_id": profile.get("user_id"), "user_name": profile.get("user_name")}
    except Exception:
        return {"authenticated": False}


@app.get("/strategies/available")
async def list_available_strategies():
    strategies_dir = Path(__file__).parent.parent / "strategies"
    result = []
    for yaml_file in sorted(strategies_dir.glob("*.yaml")):
        try:
            with open(yaml_file) as f:
                cfg = yaml.safe_load(f)
            result.append({
                "name": cfg.get("name", yaml_file.stem),
                "enabled": cfg.get("enabled", True),
                "paper_trade": cfg.get("paper_trade", True),
                "instruments": cfg.get("instruments", []),
                "timeframe": cfg.get("timeframe", "5min"),
                "capital_allocation": cfg.get("capital_allocation", 0.10),
            })
        except Exception as e:
            logger.warning("Could not parse %s: %s", yaml_file.name, e)
    return result


@app.get("/strategies")
async def list_strategies():
    result = []
    for name, s in _running_strategies.items():
        trades_today = s.state.get_int("trades_today", 0)
        open_positions = s.state.get_json("open_positions", {})
        result.append({
            "name": name,
            "enabled": s.enabled,
            "paper_trade": s.paper_trade,
            "trades_today": trades_today,
            "open_positions": len(open_positions),
        })
    return result


@app.post("/strategy/start")
async def start_strategy(req: StrategyRequest):
    if req.name in _running_strategies:
        return {"status": "already_running", "name": req.name}
    try:
        s = _loader.load_by_name(req.name)
        s.on_start()
        _event_bus.register(s)
        _running_strategies[s.name] = s
        logger.info("Started strategy %s", s.name)
        return {"status": "started", "name": s.name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/strategy/stop")
async def stop_strategy(req: StrategyRequest):
    s = _running_strategies.get(req.name)
    if not s:
        raise HTTPException(status_code=404, detail=f"Strategy '{req.name}' not running")
    try:
        s.on_stop()
        _event_bus.unregister(req.name)
        del _running_strategies[req.name]
        return {"status": "stopped", "name": req.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/strategy/pause")
async def pause_strategy(req: StrategyRequest):
    s = _running_strategies.get(req.name)
    if not s:
        raise HTTPException(status_code=404, detail=f"Strategy '{req.name}' not running")
    _event_bus.unregister(req.name)
    return {"status": "paused", "name": req.name}


@app.get("/strategy/{name}/trades")
async def get_trades(name: str):
    s = _running_strategies.get(name)
    if not s:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not running")
    return {
        "name": name,
        "trades_today": s.state.get_int("trades_today", 0),
    }


@app.get("/strategy/{name}/positions")
async def get_positions(name: str):
    s = _running_strategies.get(name)
    if not s:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not running")
    return {
        "name": name,
        "positions": s.state.get_json("open_positions", {}),
    }


@app.post("/order_update")
async def order_update(order: dict):
    await _event_bus.emit_order_update(order)
    return {"status": "ok"}


@app.get("/margins")
async def get_margins():
    try:
        data = _broker.get_margins()
        return data if data else {"equity": {}, "commodity": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/instruments/status")
async def instruments_status():
    return {
        "cached": _instrument_cache.is_cached(),
        "fetched_at": _instrument_cache.fetched_at(),
    }


@app.get("/instruments/lookup")
async def instruments_lookup(symbol: str, exchange: str):
    token = _instrument_cache.get_token(symbol.upper(), exchange.upper())
    if token is None:
        raise HTTPException(status_code=404, detail=f"{exchange.upper()}:{symbol.upper()} not found in cache")
    detail = _instrument_cache.get_instrument(token)
    return {"symbol": symbol.upper(), "exchange": exchange.upper(), "instrument_token": token, "detail": detail}


@app.get("/instruments/search")
async def instruments_search(q: str, exchange: str | None = None, fuzzy: bool = False):
    if fuzzy:
        results = _instrument_cache.fuzzy_search(q, exchange)
    else:
        results = _instrument_cache.search(q, exchange)
    return {"query": q, "exchange": exchange, "fuzzy": fuzzy, "results": results}


@app.post("/instruments/refresh")
async def instruments_refresh():
    """Force re-fetch instruments from Kite (e.g. after expiry rollover)."""
    try:
        count = await asyncio.get_event_loop().run_in_executor(
            None, _instrument_cache.fetch_and_cache
        )
        _kite_instruments_cache.clear()
        return {"status": "ok", "instruments_cached": count, "fetched_at": _instrument_cache.fetched_at()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/instruments/cache")
async def instruments_cache_file():
    """Serve today's instrument JSON file for direct frontend consumption."""
    f = _instrument_cache.today_cache_file()
    if not f:
        raise HTTPException(
            status_code=404,
            detail="No instrument cache file for today — authenticate or trigger a refresh first.",
        )
    return FileResponse(f, media_type="application/json", filename=f.name)


# In-memory cache for raw kite.instruments() lists (keyed by exchange).
# Separate from InstrumentCache (Redis) — used by symbol/option-chain UI endpoints.
_kite_instruments_cache: dict[str, list] = {}


def _require_auth() -> None:
    """Raise 503 if no Kite access token is present."""
    if not _redis.get("kite:access_token"):
        raise HTTPException(status_code=503, detail="not_authenticated")


def _cached_instruments(exchange: str) -> list:
    """Return full Kite instruments list for an exchange, cached in memory."""
    ex = exchange.upper()
    if ex not in _kite_instruments_cache:
        _kite_instruments_cache[ex] = _kite.instruments(ex)
    return _kite_instruments_cache[ex]


def _resolve_fno_underlying(inst: dict) -> tuple[str, str]:
    """Resolve a cached instrument to (fno_exchange, fno_underlying_name) for expiry / option-chain lookup.

    - Index tradingsymbols ("NIFTY 50") use the explicit map in InstrumentCache.
    - Equities, FUT, and option contracts fall back to the instrument's `name` field on NFO/BFO.
    """
    tradingsymbol = (inst.get("tradingsymbol") or "").upper()
    exchange = (inst.get("exchange") or "").upper()
    fno_exchange, fno_symbol = _instrument_cache.resolve_fno(tradingsymbol, exchange)
    if fno_exchange != exchange:
        return fno_exchange, fno_symbol
    name = (tradingsymbol).upper()
    fno_exchange = {"NSE": "NFO", "BSE": "BFO"}.get(exchange, exchange)
    return fno_exchange, name


def _underlying_spot_ltp(instrument_token: int) -> float:
    """Best-effort underlying last price for ATM selection, looked up directly by instrument_token."""
    try:
        data = _kite.quote([int(instrument_token)])
        q = data.get(str(instrument_token)) or data.get(instrument_token)
        if q:
            lp = q.get("last_price") or 0.0
            if lp > 0:
                return float(lp)
    except Exception:
        pass
    return 0.0


@app.get("/instruments/underlyings")
async def instruments_underlyings(q: str):
    """Return unique underlying names matching the query (for search bar autocomplete)."""
    # Auto-populate the cache on first search if we have a token but cache is cold.
    if not _instrument_cache.is_cached() and _redis.get("kite:access_token"):
        try:
            count = await asyncio.get_event_loop().run_in_executor(
                None, _instrument_cache.fetch_and_cache
            )
            logger.info("Instrument cache auto-populated on search: %d instruments", count)
        except Exception as e:
            logger.warning("Auto cache populate failed: %s", e)

    if not q.strip():
        return {"results": [], "cache_populated": _instrument_cache.is_cached()}

    # search() only returns {tradingsymbol, exchange, instrument_token} — fetch full details.
    def _enrich(hits: list[dict]) -> list[dict]:
        enriched = []
        for hit in hits:
            detail = _instrument_cache.get_instrument(hit["instrument_token"])
            if detail:
                enriched.append(detail)
        return enriched

    results: list[dict] = []
    seen: set[int] = set()

    # NSE + BSE: equities and INDICES (e.g. "NIFTY 50") — both routed via instrument_token
    for exch in ("NSE", "BSE"):
        for detail in _enrich(_instrument_cache.search(q.upper(), exch)):
            token = detail.get("instrument_token")
            if token is None or token in seen:
                continue
            segment = detail.get("segment", "")
            itype = detail.get("instrument_type", "")
            if segment == "INDICES":
                seen.add(token)
                results.append({
                    "symbol": detail.get("tradingsymbol", ""),
                    "exchange": exch,
                    "instrument_type": "INDICES",
                    "instrument_token": token,
                })
            elif itype == "EQ":
                seen.add(token)
                results.append({
                    "symbol": detail.get("tradingsymbol", ""),
                    "exchange": exch,
                    "instrument_type": "EQ",
                    "instrument_token": token,
                })

    # NFO + BFO: individual FUT contracts (option chain is reachable via the underlying instead)
    for exch in ("NFO", "BFO"):
        for detail in _enrich(_instrument_cache.search(q.upper(), exch)):
            if detail.get("instrument_type") != "FUT":
                continue
            token = detail.get("instrument_token")
            if token is None or token in seen:
                continue
            seen.add(token)
            results.append({
                "symbol": detail.get("tradingsymbol", ""),
                "exchange": exch,
                "instrument_type": "FUT",
                "instrument_token": token,
            })

    return {"results": results[:20], "cache_populated": _instrument_cache.is_cached()}


@app.get("/instruments/{instrument_token}/quote")
async def instrument_quote(instrument_token: int):
    """Return live OHLCV quote for an instrument identified by its instrument_token."""
    _require_auth()
    inst = _instrument_cache.get_instrument(instrument_token)
    if not inst:
        raise HTTPException(status_code=404, detail=f"instrument_token {instrument_token} not found")

    try:
        data = _kite.quote([instrument_token])
        q = data.get(str(instrument_token)) or data.get(instrument_token)
        if not q:
            raise HTTPException(status_code=404, detail=f"No quote returned for {instrument_token}")
        ohlc = q.get("ohlc", {})
        ltp = q.get("last_price", 0.0)
        prev_close = ohlc.get("close", ltp) or ltp
        change = round(ltp - prev_close, 2)
        change_pct = round(change / prev_close * 100, 2) if prev_close else 0.0
        return {
            "symbol": inst.get("tradingsymbol", ""),
            "exchange": inst.get("exchange", ""),
            "instrument_token": instrument_token,
            "ltp": ltp,
            "open": ohlc.get("open", 0.0),
            "high": ohlc.get("high", 0.0),
            "low": ohlc.get("low", 0.0),
            "close": prev_close,
            "volume": q.get("volume", 0),
            "change": change,
            "change_pct": change_pct,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/instruments/{instrument_token}/expiries")
async def instrument_expiries(instrument_token: int):
    """Return the nearest upcoming expiry dates (at most MAX_SYMBOL_EXPIRIES) for an underlying
    identified by its instrument_token.

    Traverses instruments once, keeping only the k smallest unique future expiries via a
    bounded heap; does not build or sort the full distinct-expiry set.
    """
    _require_auth()
    inst = _instrument_cache.get_instrument(instrument_token)
    if not inst:
        raise HTTPException(status_code=404, detail=f"instrument_token {instrument_token} not found")
    exchange, symbol = _resolve_fno_underlying(inst)
    try:
        instruments = await asyncio.get_event_loop().run_in_executor(
            None, _cached_instruments, exchange
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    today = datetime.date.today()
    sym_u = symbol.upper()
    k = MAX_SYMBOL_EXPIRIES
    seen: set[datetime.date] = set()
    # min-heap of -ordinal: heap[0] is -max(seen) among kept expiries
    worst_heap: list[int] = []

    for inst in instruments:
        if inst.get("name", "").upper() != sym_u:
            continue
        d = inst.get("expiry")
        if not d or d < today:
            continue
        if d in seen:
            continue
        o = d.toordinal()
        if len(seen) < k:
            seen.add(d)
            heapq.heappush(worst_heap, -o)
        elif o < -worst_heap[0]:
            popped = heapq.heappop(worst_heap)
            old = datetime.date.fromordinal(-popped)
            seen.remove(old)
            seen.add(d)
            heapq.heappush(worst_heap, -o)

    return {
        "symbol": sym_u,
        "exchange": exchange.upper(),
        "expiries": [e.isoformat() for e in sorted(seen)],
    }


@app.get("/instruments/{instrument_token}/option-chain")
async def instrument_option_chain(instrument_token: int, expiry: str):
    """Return option chain rows near ATM: at most MAX_OPTION_CHAIN_STRIKES_EACH_SIDE strikes
    below and above ATM (ATM row included), with LTP per leg when available."""
    _require_auth()
    inst = _instrument_cache.get_instrument(instrument_token)
    if not inst:
        raise HTTPException(status_code=404, detail=f"instrument_token {instrument_token} not found")
    exchange, symbol = _resolve_fno_underlying(inst)

    try:
        expiry_date = datetime.date.fromisoformat(expiry)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid expiry '{expiry}', expected YYYY-MM-DD")

    try:
        instruments = await asyncio.get_event_loop().run_in_executor(
            None, _cached_instruments, exchange
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    chain_insts = [
        inst for inst in instruments
        if inst.get("name", "").upper() == symbol.upper()
        and inst.get("expiry") == expiry_date
        and inst.get("instrument_type") in ("CE", "PE")
    ]

    if not chain_insts:
        raise HTTPException(
            status_code=404,
            detail=f"No option chain found for {symbol.upper()} expiry {expiry}",
        )

    # Build strike map (full expiry first, then narrow to ATM window before LTP batch)
    strikes: dict[float, dict] = {}
    for inst in chain_insts:
        strike = inst["strike"]
        itype = inst["instrument_type"]
        if strike not in strikes:
            strikes[strike] = {"CE": None, "PE": None}
        strikes[strike][itype] = {
            "tradingsymbol": inst["tradingsymbol"],
            "lot_size": inst["lot_size"],
            "ltp": 0.0,
        }

    sorted_strikes = sorted(strikes.keys())
    half = MAX_OPTION_CHAIN_STRIKES_EACH_SIDE
    spot = _underlying_spot_ltp(instrument_token)
    if spot > 0:
        atm_strike = min(sorted_strikes, key=lambda s: abs(s - spot))
        atm_i = sorted_strikes.index(atm_strike)
    else:
        atm_i = len(sorted_strikes) // 2

    lo = max(0, atm_i - half)
    hi = min(len(sorted_strikes), atm_i + half + 1)
    window_strikes = sorted_strikes[lo:hi]
    strike_keep = frozenset(window_strikes)

    strikes = {k: strikes[k] for k in window_strikes}
    chain_insts = [inst for inst in chain_insts if inst["strike"] in strike_keep]

    # Batch LTP fetch — failure is non-fatal, chain still renders
    try:
        all_syms = [inst["tradingsymbol"] for inst in chain_insts]
        keys = [f"{exchange.upper()}:{s}" for s in all_syms]
        ltp_data = _kite.ltp(keys)
        sym_ltp = {k.split(":", 1)[1]: v.get("last_price", 0.0) for k, v in ltp_data.items()}
        for strike_data in strikes.values():
            for leg in ("CE", "PE"):
                if strike_data[leg]:
                    ts = strike_data[leg]["tradingsymbol"]
                    strike_data[leg]["ltp"] = sym_ltp.get(ts, 0.0)
    except Exception:
        pass

    chain = [
        {"strike": strike, "ce": data["CE"], "pe": data["PE"]}
        for strike, data in sorted(strikes.items())
    ]

    return {
        "symbol": symbol.upper(),
        "exchange": exchange.upper(),
        "expiry": expiry,
        "chain": chain,
    }


class TelegramTestRequest(BaseModel):
    message: str = "🔔 Test alert from Kite Trader platform"


@app.post("/telegram/test")
async def telegram_test(req: TelegramTestRequest = None):
    body = req or TelegramTestRequest()
    ok = await send_alert(body.message)
    return {"sent": ok}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/portfolio")
async def portfolio():
    daily_pnl = float(_redis.get("portfolio:daily_pnl") or 0)
    margin_used_pct = float(_redis.get("portfolio:margin_used_pct") or 0)
    total_capital = float(os.getenv("TOTAL_CAPITAL", 500000))
    daily_loss_cap = float(os.getenv("GLOBAL_DAILY_LOSS_CAP_PCT", 0.03)) * total_capital
    return {
        "daily_pnl": round(daily_pnl, 2),
        "daily_loss_cap": round(daily_loss_cap, 2),
        "margin_used_pct": round(margin_used_pct * 100, 2),
        "max_margin_utilisation_pct": float(os.getenv("MAX_MARGIN_UTILISATION_PCT", 0.70)) * 100,
        "strategies_running": list(_running_strategies.keys()),
    }


def _build_ws_payload() -> dict:
    daily_pnl = float(_redis.get("portfolio:daily_pnl") or 0)
    margin_used_pct = float(_redis.get("portfolio:margin_used_pct") or 0)
    total_capital = float(os.getenv("TOTAL_CAPITAL", 500000))
    daily_loss_cap = float(os.getenv("GLOBAL_DAILY_LOSS_CAP_PCT", 0.03)) * total_capital

    strategies = []
    positions = {}
    for name, s in _running_strategies.items():
        open_pos = s.state.get_json("open_positions", {})
        strategies.append({
            "name": name,
            "enabled": s.enabled,
            "paper_trade": s.paper_trade,
            "status": "running",
            "trades_today": s.state.get_int("trades_today", 0),
            "open_positions": len(open_pos),
        })
        positions[name] = open_pos

    return {
        "portfolio": {
            "daily_pnl": round(daily_pnl, 2),
            "daily_loss_cap": round(daily_loss_cap, 2),
            "margin_used_pct": round(margin_used_pct * 100, 2),
            "strategies_running": list(_running_strategies.keys()),
        },
        "strategies": strategies,
        "positions": positions,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            payload = _build_ws_payload()
            await websocket.send_json(payload)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error: %s", e)


@app.websocket("/ws/quotes")
async def ws_quotes(websocket: WebSocket):
    """Multiplexed real-time tick stream. Client sends subscribe/unsubscribe JSON messages."""
    await websocket.accept()

    if not _data_feed or not _event_bus:
        await websocket.send_json({"error": "Platform not authenticated yet"})
        await websocket.close()
        return

    key = f"ws_quotes_{id(websocket)}"
    subscribed_tokens: set[int] = set()
    token_to_symbol: dict[int, str] = {}
    loop = asyncio.get_event_loop()

    def on_tick(tick: dict):
        token = tick.get("instrument_token")
        ts = tick.get("timestamp")
        asyncio.run_coroutine_threadsafe(
            websocket.send_json({
                "token": token,
                "ltp": tick.get("last_price"),
                "volume": tick.get("volume"),
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts or ""),
            }),
            loop,
        )

    _event_bus.register_quote_subscriber(key, subscribed_tokens, on_tick)
    logger.info("ws_quotes: client connected key=%s", key)

    try:
        while True:
            msg = await websocket.receive_json()
            action = msg.get("action")
            token = msg.get("token")
            if not isinstance(token, int):
                continue
            if action == "subscribe" and token not in subscribed_tokens:
                symbol = str(msg.get("symbol", token))
                subscribed_tokens.add(token)
                token_to_symbol[token] = symbol
                _data_feed.add_subscription(token, symbol)
                logger.debug("ws_quotes: subscribed token=%d symbol=%s", token, symbol)
            elif action == "unsubscribe" and token in subscribed_tokens:
                subscribed_tokens.discard(token)
                sym = token_to_symbol.pop(token, str(token))
                _data_feed.remove_subscription(token)
                logger.debug("ws_quotes: unsubscribed token=%d symbol=%s", token, sym)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("ws_quotes: connection closed key=%s: %s", key, e)
    finally:
        for token in list(subscribed_tokens):
            _data_feed.remove_subscription(token)
        _event_bus.unregister_quote_subscriber(key)
        logger.info("ws_quotes: client disconnected key=%s", key)
