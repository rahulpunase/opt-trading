"""Shared OHLCV candle store with historical backfill + live aggregation.

Single source of truth for candles across all strategies. On warmup, fetches
historical OHLCV from Kite's historical_data API; thereafter, ingests live
ticks and emits closed candles to the event bus.
"""
import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger("candles")
IST = ZoneInfo("Asia/Kolkata")

TIMEFRAME_SECONDS: dict[str, int] = {
    "1min": 60,
    "3min": 180,
    "5min": 300,
    "10min": 600,
    "15min": 900,
    "30min": 1800,
    "60min": 3600,
    "daily": 86400,
}

# Map our timeframe keys to the strings Kite's historical_data API expects.
KITE_INTERVAL: dict[str, str] = {
    "1min": "minute",
    "3min": "3minute",
    "5min": "5minute",
    "10min": "10minute",
    "15min": "15minute",
    "30min": "30minute",
    "60min": "60minute",
    "daily": "day",
}

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15


def _market_open_today(now: datetime) -> datetime:
    return now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)


def _bucket_start(ts: datetime, tf_seconds: int) -> int:
    return int(ts.timestamp() // tf_seconds) * tf_seconds


class CandleStore:
    def __init__(self, kite, instrument_cache, event_bus, maxlen: int = 500):
        self._kite = kite
        self._instrument_cache = instrument_cache
        self._event_bus = event_bus
        self._maxlen = maxlen

        # (symbol, tf) → deque[candle dict]   (oldest → newest, all closed)
        self._buffers: dict[tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=self._maxlen))
        # (symbol, tf) → live (open) bucket state
        self._live: dict[tuple[str, str], dict] = {}
        # (symbol, tf) → True once warmup has populated history
        self._warmed: set[tuple[str, str]] = set()
        # symbol → set of timeframes registered (drives ingest_tick aggregation)
        self._symbol_tfs: dict[str, set[str]] = defaultdict(set)
        # Per-(symbol, tf) lock to prevent concurrent warmups
        self._warmup_locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Capture the loop so ingest_tick (called from KiteTicker thread) can dispatch coroutines."""
        self._loop = loop

    def _lock_for(self, key: tuple[str, str]) -> asyncio.Lock:
        lock = self._warmup_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._warmup_locks[key] = lock
        return lock

    async def warmup(self, symbol: str, exchange: str, timeframe: str, lookback_candles: int) -> int:
        """Idempotent backfill via kite.historical_data. Returns number of candles loaded."""
        if timeframe not in TIMEFRAME_SECONDS:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        key = (symbol, timeframe)
        async with self._lock_for(key):
            if key in self._warmed:
                return len(self._buffers[key])

            token = self._instrument_cache.get_token(symbol, exchange) if self._instrument_cache else None
            if token is None:
                logger.warning("CandleStore: cannot warmup %s/%s — no instrument token", exchange, symbol)
                self._warmed.add(key)
                self._symbol_tfs[symbol].add(timeframe)
                return 0

            tf_seconds = TIMEFRAME_SECONDS[timeframe]
            interval = KITE_INTERVAL[timeframe]
            now = datetime.now(tz=IST)

            if timeframe == "daily":
                from_date = now - timedelta(days=max(lookback_candles, 1) * 2)  # weekend padding
            else:
                from_date = now - timedelta(seconds=lookback_candles * tf_seconds)
                from_date = max(from_date, _market_open_today(now))

            try:
                rows = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._kite.historical_data(token, from_date, now, interval),
                )
            except Exception as e:
                logger.error("CandleStore: historical_data failed symbol=%s tf=%s err=%s", symbol, timeframe, e)
                self._warmed.add(key)
                self._symbol_tfs[symbol].add(timeframe)
                return 0

            buf = self._buffers[key]
            for row in rows:
                ts = row["date"]
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=IST)
                else:
                    ts = ts.astimezone(IST)
                buf.append({
                    "symbol": symbol,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row.get("volume", 0)),
                    "timestamp": ts,
                })

            self._warmed.add(key)
            self._symbol_tfs[symbol].add(timeframe)
            logger.info(
                "CandleStore: warmup symbol=%s tf=%s loaded=%d candles (token=%d)",
                symbol, timeframe, len(buf), token,
            )
            return len(buf)

    def ingest_tick(self, symbol: str, price: float, volume: int, ts: datetime) -> None:
        """Called by DataFeed for every tick. Aggregates only into timeframes that have been warmed up."""
        timeframes = self._symbol_tfs.get(symbol)
        if not timeframes:
            return
        for tf in timeframes:
            self._aggregate(symbol, tf, price, volume, ts)

    def _aggregate(self, symbol: str, tf: str, price: float, volume: int, ts: datetime) -> None:
        tf_seconds = TIMEFRAME_SECONDS[tf]
        bucket = _bucket_start(ts, tf_seconds)
        key = (symbol, tf)
        state = self._live.get(key)

        if state is None or state["bucket"] != bucket:
            if state is not None:
                closed = {
                    "symbol": symbol,
                    "open": state["open"],
                    "high": state["high"],
                    "low": state["low"],
                    "close": state["close"],
                    "volume": state["volume"],
                    "timestamp": datetime.fromtimestamp(state["bucket"], tz=IST),
                }
                self._buffers[key].append(closed)
                if self._loop is not None:
                    asyncio.run_coroutine_threadsafe(
                        self._event_bus.emit_candle(symbol, tf, closed),
                        self._loop,
                    )

            self._live[key] = {
                "bucket": bucket,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
            }
        else:
            state["high"] = max(state["high"], price)
            state["low"] = min(state["low"], price)
            state["close"] = price
            state["volume"] += volume

    def history(self, symbol: str, timeframe: str, n: Optional[int] = None) -> list[dict]:
        """Return last n closed candles (historical + live), oldest first. Returns a list copy."""
        buf = self._buffers.get((symbol, timeframe))
        if not buf:
            return []
        if n is None or n >= len(buf):
            return list(buf)
        return list(buf)[-n:]

    def latest(self, symbol: str, timeframe: str) -> Optional[dict]:
        buf = self._buffers.get((symbol, timeframe))
        if not buf:
            return None
        return buf[-1]

    def subscribed_timeframes(self, symbol: str) -> set[str]:
        return set(self._symbol_tfs.get(symbol, ()))

    def is_warmed(self, symbol: str, timeframe: str) -> bool:
        return (symbol, timeframe) in self._warmed
