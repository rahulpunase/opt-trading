import json
import logging
import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger("instrument_cache")

_IST = ZoneInfo("Asia/Kolkata")
_EXCHANGES = ["NSE", "BSE", "NFO", "BFO", "MCX", "CDS"]

# File cache: data/instruments_YYYY-MM-DD.json (one file per trading day)
_CACHE_DIR = Path(__file__).parent.parent / "data"

# Maps "{fno_exchange}:{fno_name}" → NSE/BSE index tradingsymbol.
# Needed because index F&O instruments use a short name (e.g. "NIFTY") that
# differs from the INDICES segment tradingsymbol (e.g. "NIFTY 50").
_FNO_TO_INDEX: dict[str, str] = {
    "NFO:NIFTY":      "NIFTY 50",
    "NFO:BANKNIFTY":  "NIFTY BANK",
    "NFO:FINNIFTY":   "NIFTY FIN SERVICE",
    "NFO:MIDCPNIFTY": "NIFTY MID SELECT",
    "NFO:NIFTYNXT50": "NIFTY NEXT 50",
    "BFO:BANKEX":     "BANKEX",
    "BFO:SENSEX":     "SENSEX",
    "BFO:SENSEX50":   "SENSEX50",
}

# Reverse: index tradingsymbol → (fno_exchange, fno_name)
_INDEX_TO_FNO: dict[str, tuple[str, str]] = {
    v: tuple(k.split(":", 1))  # type: ignore[misc]
    for k, v in _FNO_TO_INDEX.items()
}


def _today_file() -> Path:
    return _CACHE_DIR / f"instruments_{datetime.date.today().isoformat()}.json"


def _expiry_str(val) -> str | None:
    """Normalise expiry to ISO string regardless of whether it's a date or already a string."""
    if val is None:
        return None
    return val if isinstance(val, str) else val.isoformat()


class InstrumentCache:
    def __init__(self, kite):
        self._kite = kite
        # Single atomic in-memory store. None = not loaded yet.
        # Structure: {"lookup": {exchange: {symbol: token}},
        #             "details": {token: dict},
        #             "by_exchange": {exchange: [dict, ...]},
        #             "fetched_at": ISO str}
        self._data: dict | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_and_cache(self) -> int:
        """
        Load today's file cache if it exists, otherwise fetch from Kite and
        write the file. Builds the in-memory index either way.
        Returns the total number of instruments loaded.
        """
        _CACHE_DIR.mkdir(exist_ok=True)
        today_file = _today_file()

        if today_file.exists():
            logger.info("Loading instruments from file cache: %s", today_file)
            with open(today_file) as f:
                payload = json.load(f)
            if "grouped" in payload:
                instruments = self._flatten_grouped(payload["grouped"])
            else:
                instruments = payload["instruments"]  # old-format backward compat
            fetched_at = payload.get("fetched_at", datetime.datetime.now(_IST).isoformat())
            logger.info("Loaded %d instruments from file cache", len(instruments))
        else:
            logger.info("Fetching instruments from Kite...")
            raw = self._kite.instruments()
            logger.info("Fetched %d instruments total", len(raw))
            instruments = self._normalise(raw)
            fetched_at = datetime.datetime.now(_IST).isoformat()
            self._write_file(today_file, instruments, fetched_at)
            self._cleanup_old_files(today_file)

        self._build_index(instruments, fetched_at)
        return len(instruments)

    def today_cache_file(self) -> Path | None:
        """Return today's JSON file path if it exists, else None."""
        f = _today_file()
        return f if f.exists() else None

    def is_cached(self) -> bool:
        return self._data is not None

    def fetched_at(self) -> str | None:
        return self._data["fetched_at"] if self._data else None

    def get_token(self, tradingsymbol: str, exchange: str) -> int | None:
        """Resolve a symbol+exchange pair to an instrument_token."""
        if not self._data:
            return None
        return self._data["lookup"].get(exchange.upper(), {}).get(tradingsymbol)

    def get_tokens(self, symbols: list[str], exchange: str) -> list[int]:
        """Bulk-resolve a list of symbols for one exchange. Skips unknowns."""
        if not symbols or not self._data:
            return []
        lookup = self._data["lookup"].get(exchange.upper(), {})
        tokens = []
        for sym in symbols:
            token = lookup.get(sym)
            if token is not None:
                tokens.append(token)
            else:
                # For derivatives exchanges, try auto-resolving to the front-month futures contract.
                if exchange.upper() in ("NFO", "BFO", "MCX", "CDS"):
                    token = self.get_front_month_futures_token(sym, exchange)
                if token is not None:
                    tokens.append(token)
                else:
                    logger.warning("No instrument token found for %s:%s", exchange, sym)
        return tokens

    def get_front_month_futures_token(self, base_symbol: str, exchange: str) -> int | None:
        """
        Resolve a bare symbol (e.g. "RELIANCE") to the nearest-expiry FUT contract
        on a derivatives exchange (NFO/BFO/MCX). Returns the instrument_token or None.
        """
        if not self._data:
            return None
        today = datetime.date.today().isoformat()
        best_token: int | None = None
        best_expiry: str | None = None
        for inst in self._data["by_exchange"].get(exchange.upper(), []):
            if inst.get("instrument_type") != "FUT":
                continue
            inst_name = inst.get("name", "").upper()
            inst_sym = inst.get("tradingsymbol", "").upper()
            if inst_name != base_symbol.upper() and not inst_sym.startswith(base_symbol.upper()):
                continue
            expiry = inst.get("expiry")
            if not expiry or expiry < today:
                continue
            if best_expiry is None or expiry < best_expiry:
                best_expiry = expiry
                best_token = inst["instrument_token"]
        if best_token is not None:
            logger.info(
                "Resolved %s:%s → front-month FUT token=%s expiry=%s",
                exchange, base_symbol, best_token, best_expiry,
            )
        return best_token

    def get_instrument(self, token: int | str) -> dict | None:
        """Return the full instrument dict for a given token."""
        if not self._data:
            return None
        return self._data["details"].get(int(token))

    def resolve_fno(self, symbol: str, exchange: str) -> tuple[str, str]:
        """
        Translate an index tradingsymbol to its F&O exchange + name.
        E.g. ("NIFTY 50", "NSE") → ("NFO", "NIFTY").
        Returns (exchange, symbol) unchanged when no mapping exists (equity case).
        """
        sym_upper = symbol.upper()
        for index_ts, (fno_ex, fno_name) in _INDEX_TO_FNO.items():
            if index_ts.upper() == sym_upper:
                return fno_ex, fno_name
        return exchange, symbol

    def fuzzy_search(
        self,
        query: str,
        exchange: str | None = None,
        limit: int = 20,
        score_cutoff: int = 60,
    ) -> list[dict]:
        """Fuzzy search across tradingsymbol and name fields using rapidfuzz."""
        if not self._data or not query:
            return []
        from rapidfuzz import fuzz, process

        exchanges = [exchange.upper()] if exchange else _EXCHANGES
        candidates = []
        for exch in exchanges:
            for inst in self._data["by_exchange"].get(exch, []):
                candidates.append(inst)

        symbols = [c["tradingsymbol"] for c in candidates]
        sym_hits = process.extract(
            query.upper(), symbols, scorer=fuzz.WRatio,
            limit=limit * 2, score_cutoff=score_cutoff,
        )

        names = [c.get("name", "") for c in candidates]
        name_hits = process.extract(
            query.upper(), names, scorer=fuzz.WRatio,
            limit=limit * 2, score_cutoff=score_cutoff,
        )

        seen: set[int] = set()
        results = []
        for _, score, idx in sorted(sym_hits + name_hits, key=lambda x: -x[1]):
            inst = candidates[idx]
            token = inst["instrument_token"]
            if token in seen:
                continue
            seen.add(token)
            results.append({
                "tradingsymbol": inst["tradingsymbol"],
                "name": inst.get("name", ""),
                "exchange": inst["exchange"],
                "instrument_token": token,
                "score": score,
            })
            if len(results) >= limit:
                break

        return results

    def search(self, query: str, exchange: str | None = None) -> list[dict]:
        """Prefix search across tradingsymbols. Returns up to 50 results."""
        if not self._data:
            return []
        query_upper = query.upper()
        exchanges = [exchange.upper()] if exchange else _EXCHANGES
        results = []
        for exch in exchanges:
            for inst in self._data["by_exchange"].get(exch, []):
                if inst["tradingsymbol"].startswith(query_upper):
                    results.append({
                        "tradingsymbol": inst["tradingsymbol"],
                        "exchange": exch,
                        "instrument_token": inst["instrument_token"],
                    })
                    if len(results) >= 50:
                        return results
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_index(self, instruments: list[dict], fetched_at: str) -> None:
        """Build in-memory lookup structures and swap them in atomically."""
        lookup: dict[str, dict[str, int]] = {}
        details: dict[int, dict] = {}
        by_exchange: dict[str, list[dict]] = {}

        for inst in instruments:
            exchange = inst.get("exchange", "")
            symbol = inst.get("tradingsymbol", "")
            token = inst.get("instrument_token")
            if not (exchange and symbol and token is not None):
                continue

            lookup.setdefault(exchange, {})[symbol] = token
            details[token] = inst
            by_exchange.setdefault(exchange, []).append(inst)

        # Single assignment — atomic under CPython's GIL
        self._data = {
            "lookup": lookup,
            "details": details,
            "by_exchange": by_exchange,
            "fetched_at": fetched_at,
        }
        logger.info("In-memory index built: %d instruments across %d exchanges", len(details), len(by_exchange))

    def _normalise(self, raw: list[dict]) -> list[dict]:
        """Convert Kite instrument dicts to a JSON-serialisable form."""
        out = []
        for inst in raw:
            out.append({
                "instrument_token": inst.get("instrument_token"),
                "exchange_token": inst.get("exchange_token"),
                "tradingsymbol": inst.get("tradingsymbol", ""),
                "name": inst.get("name", ""),
                "last_price": inst.get("last_price", 0),
                "expiry": _expiry_str(inst.get("expiry")),
                "strike": inst.get("strike", 0),
                "tick_size": inst.get("tick_size", 0),
                "lot_size": inst.get("lot_size", 1),
                "instrument_type": inst.get("instrument_type", ""),
                "segment": inst.get("segment", ""),
                "exchange": inst.get("exchange", ""),
            })
        return out

    def _write_file(self, path: Path, instruments: list[dict], fetched_at: str) -> None:
        """Write instruments to today's JSON cache file atomically."""
        payload = {
            "date": datetime.date.today().isoformat(),
            "fetched_at": fetched_at,
            "count": len(instruments),
            "index_underlying_map": _FNO_TO_INDEX,
            "grouped": self._group_instruments(instruments),
        }
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(payload, f, separators=(",", ":"))
        tmp.rename(path)
        logger.info("Wrote instrument cache to %s (%d instruments)", path.name, len(instruments))

    def _group_instruments(self, instruments: list[dict]) -> dict:
        """Group a flat instrument list by segment → name → instrument_type, sorted by expiry/strike."""
        grouped: dict[str, dict[str, dict[str, list]]] = {}
        for inst in instruments:
            seg = inst.get("segment", "UNKNOWN")
            name = inst.get("name", "") or inst.get("tradingsymbol", "")
            itype = inst.get("instrument_type", "")
            grouped.setdefault(seg, {}).setdefault(name, {}).setdefault(itype, []).append(inst)

        for seg in grouped:
            for name in grouped[seg]:
                for itype, lst in grouped[seg][name].items():
                    grouped[seg][name][itype] = sorted(
                        lst,
                        key=lambda x: (x.get("expiry") or "", x.get("strike", 0)),
                    )
        return grouped

    def _flatten_grouped(self, grouped: dict) -> list[dict]:
        """Reconstruct a flat instrument list from the grouped file structure."""
        out = []
        for names in grouped.values():
            for itypes in names.values():
                for lst in itypes.values():
                    out.extend(lst)
        return out

    def _cleanup_old_files(self, keep: Path) -> None:
        """Delete instrument JSON files from previous days."""
        for f in _CACHE_DIR.glob("instruments_*.json"):
            if f != keep:
                f.unlink(missing_ok=True)
                logger.info("Removed old cache file: %s", f.name)
