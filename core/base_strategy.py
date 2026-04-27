from abc import ABC, abstractmethod
from typing import Optional
import logging


class BaseStrategy(ABC):
    def __init__(self, config: dict, broker, state, logger: logging.Logger):
        self.config = config
        self.broker = broker
        self.state = state
        self.logger = logger
        self.name = config["name"]
        self.enabled = config.get("enabled", True)
        self.paper_trade = config.get("paper_trade", True)
        # Populated by StrategyLoader after instrument cache lookup
        self.instrument_tokens: list[int] = []
        # Injected by StrategyLoader — used by subscribe_instrument()
        self._data_feed = None
        self._instrument_cache = None

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
        tick = {"instrument_token": int, "last_price": float, "timestamp": datetime}
        """
        ...

    @abstractmethod
    def on_order_update(self, order: dict) -> None:
        """
        Called by the Kite postback webhook when an order status changes.
        """
        ...

    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass

    def on_market_open(self) -> None:
        pass

    def on_market_close(self) -> None:
        pass

    def get_param(self, key: str, default=None):
        return self.config.get("params", {}).get(key, default)

    def get_instruments(self) -> list:
        return self.config.get("instruments", [])

    def get_timeframe(self) -> str:
        return self.config.get("timeframe", "5min")

    def get_capital_allocation(self) -> float:
        return self.config.get("capital_allocation", 0.10)

    def subscribe_instrument(self, symbol: str, exchange: str) -> None:
        """Subscribe to an instrument beyond the YAML instruments list. Call from on_start()."""
        if self._data_feed is None or self._instrument_cache is None:
            self.logger.warning("subscribe_instrument: data_feed not injected yet")
            return
        token = self._instrument_cache.get_token(symbol, exchange)
        if token:
            self._data_feed.add_subscription(token, symbol)
            self.logger.info("subscribe_instrument: %s/%s token=%d", symbol, exchange, token)
        else:
            self.logger.warning("subscribe_instrument: cannot resolve token for %s/%s", symbol, exchange)
