import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import redis as redis_lib
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from kiteconnect import KiteConnect
from pydantic import BaseModel

from alerts.telegram import send_alert
from core.data_feed import DataFeed
from core.event_bus import EventBus
from core.order_router import OrderRouter
from core.risk_gate import RiskGate
from core.state import make_redis_client
from core.strategy_loader import StrategyLoader

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _kite, _broker, _event_bus, _risk_gate, _loader

    _redis = make_redis_client()
    _kite = KiteConnect(api_key=os.getenv("KITE_API_KEY", ""))

    stored_token = _redis.get("kite:access_token")
    if stored_token:
        _kite.set_access_token(stored_token.decode())
        logger.info("Restored access_token from Redis")

    paper_default = os.getenv("PAPER_TRADE_DEFAULT", "true").lower() == "true"
    _broker = OrderRouter(_kite, paper_trade=paper_default)
    _event_bus = EventBus()
    _risk_gate = RiskGate(_redis)
    _loader = StrategyLoader(_broker, _risk_gate)
    _event_bus.start_scheduler()

    strategies = _loader.load_all()
    for s in strategies:
        try:
            s.on_start()
            _event_bus.register(s)
            _running_strategies[s.name] = s
        except Exception as e:
            logger.error("Failed to start strategy %s: %s", s.name, e)

    logger.info("Platform started with %d strategies", len(_running_strategies))
    yield

    for s in _running_strategies.values():
        try:
            s.on_stop()
        except Exception as e:
            logger.error("Error stopping %s: %s", s.name, e)
    _event_bus.stop_scheduler()


app = FastAPI(title="Kite Trader Platform", lifespan=lifespan)


class AuthRequest(BaseModel):
    request_token: str


class StrategyRequest(BaseModel):
    name: str


@app.get("/auth/login")
async def auth_login():
    url = f"https://kite.zerodha.com/connect/login?v=3&api_key={os.getenv('KITE_API_KEY', '')}"
    return {"login_url": url}


@app.post("/auth")
async def auth(req: AuthRequest):
    global _data_feed
    try:
        data = _kite.generate_session(req.request_token, api_secret=os.getenv("KITE_API_SECRET", ""))
        access_token = data["access_token"]
        _kite.set_access_token(access_token)
        _redis.set("kite:access_token", access_token)
        logger.info("Auth successful, user=%s", data.get("user_id", "unknown"))

        if _data_feed:
            _data_feed.stop()
        _data_feed = DataFeed(
            api_key=os.getenv("KITE_API_KEY", ""),
            access_token=access_token,
            event_bus=_event_bus,
            instrument_tokens=[],
        )
        _data_feed.start()

        return {
            "status": "ok",
            "access_token": access_token,
            "user_id": data.get("user_id"),
            "user_name": data.get("user_name"),
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
