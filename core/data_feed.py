import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from kiteconnect import KiteTicker

logger = logging.getLogger("data_feed")
IST = ZoneInfo("Asia/Kolkata")

TIMEFRAME_SECONDS = {
    "1min": 60,
    "5min": 300,
    "15min": 900,
    "daily": 86400,
}


class DataFeed:
    def __init__(self, api_key: str, access_token: str, event_bus, instrument_tokens: list[int]):
        self._api_key = api_key
        self._access_token = access_token
        self._event_bus = event_bus
        self._tokens = instrument_tokens
        self._ticker: KiteTicker = None
        self._candles: dict = defaultdict(lambda: defaultdict(dict))
        self._token_to_symbol: dict[int, str] = {}

    def set_token_symbol_map(self, mapping: dict[int, str]):
        self._token_to_symbol = mapping

    def start(self):
        self._ticker = KiteTicker(self._api_key, self._access_token)
        self._ticker.on_ticks = self._on_ticks
        self._ticker.on_connect = self._on_connect
        self._ticker.on_close = self._on_close
        self._ticker.on_error = self._on_error
        self._ticker.connect(threaded=True, reconnect=True, reconnect_max_delay=30, reconnect_max_tries=50)

    def stop(self):
        if self._ticker:
            self._ticker.close()

    def _on_connect(self, ws, response):
        logger.info("DataFeed: connected, subscribing %d tokens", len(self._tokens))
        ws.subscribe(self._tokens)
        ws.set_mode(ws.MODE_FULL, self._tokens)

    def _on_close(self, ws, code, reason):
        logger.warning("DataFeed: disconnected code=%s reason=%s", code, reason)

    def _on_error(self, ws, code, reason):
        logger.error("DataFeed: error code=%s reason=%s", code, reason)

    def _on_ticks(self, ws, ticks):
        for tick in ticks:
            token = tick["instrument_token"]
            symbol = self._token_to_symbol.get(token, str(token))
            last_price = tick.get("last_price", 0)
            ts = tick.get("timestamp") or datetime.now(tz=IST)

            normalized_tick = {
                "instrument_token": token,
                "symbol": symbol,
                "last_price": last_price,
                "timestamp": ts,
            }

            asyncio.run_coroutine_threadsafe(
                self._event_bus.emit_tick(normalized_tick),
                asyncio.get_event_loop(),
            )

            for tf, tf_seconds in TIMEFRAME_SECONDS.items():
                self._aggregate_candle(symbol, tf, tf_seconds, last_price, tick.get("volume_traded", 0), ts)

    def _aggregate_candle(self, symbol: str, tf: str, tf_seconds: int, price: float, volume: int, ts: datetime):
        bucket = int(ts.timestamp() // tf_seconds) * tf_seconds
        state = self._candles[symbol][tf]

        if state.get("bucket") != bucket:
            if state.get("bucket") is not None:
                closed_candle = {
                    "symbol": symbol,
                    "open": state["open"],
                    "high": state["high"],
                    "low": state["low"],
                    "close": state["close"],
                    "volume": state["volume"],
                    "timestamp": datetime.fromtimestamp(state["bucket"], tz=IST),
                }
                asyncio.run_coroutine_threadsafe(
                    self._event_bus.emit_candle(symbol, tf, closed_candle),
                    asyncio.get_event_loop(),
                )
            self._candles[symbol][tf] = {
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
