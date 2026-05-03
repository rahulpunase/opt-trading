import importlib.util
import inspect
import logging
import os
from pathlib import Path
from typing import Dict, List

import yaml

from core.base_strategy import BaseStrategy
from core.chartink_scraper import fetch_chartink_symbols
from core.state import StrategyState, make_redis_client

logger = logging.getLogger("strategy_loader")

STRATEGIES_DIR = Path(__file__).parent.parent / "strategies"


class StrategyLoader:
    def __init__(self, broker, risk_gate=None, instrument_cache=None, data_feed=None, candle_store=None):
        self._broker = broker
        self._risk_gate = risk_gate
        self._instrument_cache = instrument_cache
        self._data_feed = data_feed
        self._candle_store = candle_store
        self._redis = make_redis_client()
        self._loaded: Dict[str, BaseStrategy] = {}

    def set_data_feed(self, data_feed) -> None:
        """Called after /auth when DataFeed is started — injected into all subsequently loaded strategies."""
        self._data_feed = data_feed

    def set_candle_store(self, candle_store) -> None:
        """Called after /auth when CandleStore is constructed."""
        self._candle_store = candle_store

    def load_all(self) -> List[BaseStrategy]:
        strategies = []
        for py_file in STRATEGIES_DIR.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            try:
                strategy = self._load_file(py_file)
                if strategy:
                    strategies.append(strategy)
            except Exception as e:
                logger.error("Loader: failed to load %s: %s", py_file.name, e)
        return strategies

    def load_by_name(self, name: str) -> BaseStrategy:
        for py_file in STRATEGIES_DIR.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            yaml_file = py_file.with_suffix(".yaml")
            if not yaml_file.exists():
                continue
            config = self._load_yaml(yaml_file)
            if config.get("name") == name:
                return self._load_file(py_file)
        raise ValueError(f"Strategy '{name}' not found")

    def get_loaded(self) -> Dict[str, BaseStrategy]:
        return self._loaded

    def _load_file(self, py_file: Path):
        yaml_file = py_file.with_suffix(".yaml")
        if not yaml_file.exists():
            logger.warning("Loader: no yaml for %s, skipping", py_file.name)
            return None

        config = self._load_yaml(yaml_file)
        if not config.get("enabled", True):
            logger.info("Loader: %s disabled, skipping", py_file.name)
            return None

        screener_url = config.get("screener_url")
        if screener_url:
            screener_timeout = float(config.get("screener_timeout", 10.0))
            logger.info("Loader: fetching Chartink screener %s", screener_url)
            screener_symbols = fetch_chartink_symbols(screener_url, timeout=screener_timeout)
            if screener_symbols:
                existing = list(config.get("instruments", []) or [])
                seen = set(existing)
                for sym in screener_symbols:
                    if sym not in seen:
                        existing.append(sym)
                        seen.add(sym)
                config["instruments"] = existing
                logger.info(
                    "Loader: %s — %d screener symbols, total instruments=%d",
                    py_file.stem, len(screener_symbols), len(existing),
                )
            else:
                logger.warning(
                    "Loader: %s — Chartink screener returned no symbols, using static only",
                    py_file.stem,
                )

        module = self._import_module(py_file)
        klass = self._find_strategy_class(module)
        if not klass:
            logger.warning("Loader: no BaseStrategy subclass in %s", py_file.name)
            return None

        strat_logger = logging.getLogger(f"strategy.{config['name']}")
        state = StrategyState(config["name"], self._redis)
        strategy = klass(config, self._broker, state, strat_logger)

        self._loaded[config["name"]] = strategy
        if self._risk_gate:
            self._risk_gate.register_strategy(config["name"], strategy)

        # Inject shared infrastructure so strategies can call subscribe_instrument()
        strategy._data_feed = self._data_feed
        strategy._instrument_cache = self._instrument_cache
        strategy.candles = self._candle_store

        # Resolve symbol names → instrument tokens and attach to the strategy
        strategy.instrument_tokens = self._resolve_tokens(config)

        logger.info("Loader: loaded %s (tokens=%s)", config["name"], strategy.instrument_tokens)
        return strategy

    def _load_yaml(self, path: Path) -> dict:
        with open(path) as f:
            return yaml.safe_load(f)

    def _import_module(self, path: Path):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _find_strategy_class(self, module):
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
                return obj
        return None

    def _resolve_tokens(self, config: dict) -> list:
        """
        Resolve the strategy's `instruments` list to Kite instrument_tokens.
        Falls back to an empty list if the cache is unavailable or a symbol is unknown.
        """
        if not self._instrument_cache:
            return []
        symbols = config.get("instruments", [])
        exchange = config.get("exchange", "NSE")
        tokens = self._instrument_cache.get_tokens(symbols, exchange)
        return tokens
