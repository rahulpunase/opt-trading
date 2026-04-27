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
        self._tokens = list(instrument_tokens)
        self._ticker: KiteTicker = None
        self._loop = None
        self._candles: dict = defaultdict(lambda: defaultdict(dict))
        self._token_to_symbol: dict[int, str] = {}
        self._dynamic_refcount: dict[int, int] = {}

    def set_token_symbol_map(self, mapping: dict[int, str]):
        self._token_to_symbol = mapping

    def start(self):
        # Capture the running event loop before spawning the ticker thread
        self._loop = asyncio.get_event_loop()
        # print api key and access token
        logger.info("DataFeed: starting with api_key=%s access_token=%s", self._api_key, self._access_token)
        self._ticker = KiteTicker(
            self._api_key,
            self._access_token,
            reconnect=True,
            reconnect_max_tries=50,
            reconnect_max_delay=5,
        )
        self._ticker.on_ticks = self._on_ticks
        self._ticker.on_connect = self._on_connect
        self._ticker.on_close = self._on_close
        self._ticker.on_error = self._on_error
        self._ticker.connect(threaded=True)

    def stop(self):
        if self._ticker:
            self._ticker.close()

    def _is_connected(self) -> bool:
        return self._ticker is not None and self._ticker.is_connected()

    def add_subscription(self, token: int, symbol: str) -> None:
        """Dynamically subscribe to a token. Reference-counted so multiple consumers share one subscription."""
        self._dynamic_refcount[token] = self._dynamic_refcount.get(token, 0) + 1
        if token not in self._tokens:
            self._tokens.append(token)
            self._token_to_symbol[token] = symbol
            if self._is_connected():
                self._ticker.subscribe([token])
                self._ticker.set_mode(self._ticker.MODE_FULL, [token])
        logger.info("DataFeed: add_subscription token=%d symbol=%s refcount=%d", token, symbol, self._dynamic_refcount[token])

    def remove_subscription(self, token: int) -> None:
        """Decrement refcount; unsubscribe from KiteTicker when no consumers remain."""
        count = self._dynamic_refcount.get(token, 0) - 1
        if count <= 0:
            self._dynamic_refcount.pop(token, None)
            if token in self._tokens:
                self._tokens.remove(token)
                self._token_to_symbol.pop(token, None)
            if self._is_connected():
                self._ticker.unsubscribe([token])
            logger.info("DataFeed: remove_subscription token=%d (unsubscribed)", token)
        else:
            self._dynamic_refcount[token] = count
            logger.info("DataFeed: remove_subscription token=%d refcount=%d (still active)", token, count)

    def _on_connect(self, ws, response):
        logger.info("DataFeed: connected, subscribing %d tokens", len(self._tokens))
        if self._tokens:
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
            volume = tick.get("volume_traded", 0)
            ts = tick.get("timestamp") or datetime.now(tz=IST)

            normalized_tick = {
                "instrument_token": token,
                "symbol": symbol,
                "last_price": last_price,
                "volume": volume,
                "timestamp": ts,
            }

            asyncio.run_coroutine_threadsafe(
                self._event_bus.emit_tick(normalized_tick),
                self._loop,
            )

            for tf, tf_seconds in TIMEFRAME_SECONDS.items():
                self._aggregate_candle(symbol, tf, tf_seconds, last_price, volume, ts)

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
                    self._loop,
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
