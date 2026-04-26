import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import redis

logger = logging.getLogger("instrument_cache")

_IST = ZoneInfo("Asia/Kolkata")

# Redis key layout:
#   instruments:lookup:{EXCHANGE}   → hash  { tradingsymbol: instrument_token }
#   instruments:detail:{token}      → string  JSON of full instrument dict
#   instruments:fetched_at          → string  ISO timestamp of last fetch

_EXCHANGES = ["NSE", "BSE", "NFO", "BFO", "MCX", "CDS"]
_TTL_SECONDS = 24 * 60 * 60  # 24 hours — instruments don't change intraday


def _lookup_key(exchange: str) -> str:
    return f"instruments:lookup:{exchange.upper()}"


def _detail_key(token: int | str) -> str:
    return f"instruments:detail:{token}"


class InstrumentCache:
    def __init__(self, kite, redis_client: redis.Redis):
        self._kite = kite
        self._r = redis_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_and_cache(self) -> int:
        """
        Download ALL instruments from Kite and store in Redis.
        Returns the total number of instruments cached.

        Should be called once after successful auth each morning.
        """
        logger.info("Fetching instruments from Kite...")
        all_instruments = self._kite.instruments()  # returns list of dicts
        logger.info("Fetched %d instruments total", len(all_instruments))

        pipe = self._r.pipeline(transaction=False)

        # Delete stale lookup hashes before repopulating
        for exchange in _EXCHANGES:
            pipe.delete(_lookup_key(exchange))

        cached = 0
        for inst in all_instruments:
            exchange = inst.get("exchange", "")
            symbol = inst.get("tradingsymbol", "")
            token = inst.get("instrument_token")
            if not (exchange and symbol and token is not None):
                continue

            # symbol → token lookup per exchange
            pipe.hset(_lookup_key(exchange), symbol, str(token))

            # token → full detail (JSON)
            detail = {
                "instrument_token": token,
                "exchange_token": inst.get("exchange_token"),
                "tradingsymbol": symbol,
                "name": inst.get("name", ""),
                "last_price": inst.get("last_price", 0),
                "expiry": inst.get("expiry").isoformat() if inst.get("expiry") else None,
                "strike": inst.get("strike", 0),
                "tick_size": inst.get("tick_size", 0),
                "lot_size": inst.get("lot_size", 1),
                "instrument_type": inst.get("instrument_type", ""),
                "segment": inst.get("segment", ""),
                "exchange": exchange,
            }
            pipe.set(_detail_key(token), json.dumps(detail), ex=_TTL_SECONDS)
            cached += 1

        # Set TTL on lookup hashes
        for exchange in _EXCHANGES:
            pipe.expire(_lookup_key(exchange), _TTL_SECONDS)

        # Record when we fetched
        pipe.set(
            "instruments:fetched_at",
            datetime.now(_IST).isoformat(),
            ex=_TTL_SECONDS,
        )

        pipe.execute()
        logger.info("Cached %d instruments in Redis (TTL=%ds)", cached, _TTL_SECONDS)
        return cached

    def is_cached(self) -> bool:
        return bool(self._r.exists("instruments:fetched_at"))

    def fetched_at(self) -> str | None:
        val = self._r.get("instruments:fetched_at")
        return val.decode() if val else None

    def get_token(self, tradingsymbol: str, exchange: str) -> int | None:
        """Resolve a symbol+exchange pair to an instrument_token."""
        val = self._r.hget(_lookup_key(exchange), tradingsymbol)
        return int(val.decode()) if val else None

    def get_tokens(self, symbols: list[str], exchange: str) -> list[int]:
        """Bulk-resolve a list of symbols for one exchange. Skips unknowns."""
        if not symbols:
            return []
        pipe = self._r.pipeline(transaction=False)
        for sym in symbols:
            pipe.hget(_lookup_key(exchange), sym)
        results = pipe.execute()
        tokens = []
        for sym, val in zip(symbols, results):
            if val:
                tokens.append(int(val.decode()))
            else:
                logger.warning("No instrument token found for %s:%s", exchange, sym)
        return tokens

    def get_instrument(self, token: int | str) -> dict | None:
        """Return the full instrument dict for a given token."""
        val = self._r.get(_detail_key(token))
        return json.loads(val.decode()) if val else None

    def search(self, query: str, exchange: str | None = None) -> list[dict]:
        """
        Simple prefix search across symbol names.
        Useful for debugging / the /instruments/search endpoint.
        Searches only the exchanges specified (all if None).
        """
        query_upper = query.upper()
        exchanges = [exchange.upper()] if exchange else _EXCHANGES
        results = []
        for exch in exchanges:
            key = _lookup_key(exch)
            # HSCAN to avoid blocking Redis on large hashes
            cursor = 0
            while True:
                cursor, items = self._r.hscan(key, cursor, match=f"{query_upper}*", count=100)
                for sym_bytes, token_bytes in items.items():
                    results.append({"tradingsymbol": sym_bytes.decode(), "exchange": exch, "instrument_token": int(token_bytes.decode())})
                if cursor == 0:
                    break
            if len(results) >= 50:  # cap results
                break
        return results[:50]
