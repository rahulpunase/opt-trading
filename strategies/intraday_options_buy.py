import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import ta as ta_lib

from core.base_strategy import BaseStrategy

IST = ZoneInfo("Asia/Kolkata")


class IntradayOptionsBuy(BaseStrategy):
    """
    Intraday options buying strategy using EMA crossover + RSI confirmation.

    Signal logic (evaluated on every closed candle):
      - LONG  : fast EMA crosses above slow EMA  AND  RSI > rsi_entry_long  (default 55)
      - SHORT : fast EMA crosses below slow EMA  AND  RSI < rsi_entry_short (default 45)
      Default EMAs: 9 (fast) / 21 (slow), RSI period: 14.

    Entry: MARKET order placed immediately on signal. One position per symbol at a time.
    Caps: max_trades_per_day (default 4) and max_open_positions (default 2) enforced
          before every entry.

    Risk management (monitored tick-by-tick):
      - Stop loss : sl_pct     % from entry price (default 0.35 %)
      - Target    : target1_pct% from entry price (default 0.50 %)
      Exit fires as a MARKET order the moment either level is breached.

    End-of-day safety: all open positions are force-closed at market close (3:30 PM IST)
    via on_market_close(), ensuring no overnight exposure.

    State persistence: trade count and open positions are written to Redis on every
    change and restored on on_start(), so the strategy survives container restarts
    without losing intraday context.
    """

    def __init__(self, config, broker, state, logger):
        super().__init__(config, broker, state, logger)
        self._trades_today = 0
        self._open_positions: dict[str, dict] = {}

    def on_start(self) -> None:
        self._trades_today = self.state.get_int("trades_today", 0)
        self._open_positions = self.state.get_json("open_positions", {})
        self.logger.info("%s started | paper_trade=%s", self.name, self.paper_trade)

    def on_stop(self) -> None:
        self.state.set_json("open_positions", self._open_positions)
        self.logger.info("%s stopped", self.name)

    def on_market_open(self) -> None:
        self._trades_today = 0
        self._open_positions = {}
        self.state.set("trades_today", 0)
        self.state.set_json("open_positions", {})
        self.logger.info("%s: market open reset", self.name)

    def on_market_close(self) -> None:
        try:
            for symbol, pos in list(self._open_positions.items()):
                self.logger.info(
                    "%s: force-closing position at market close | symbol=%s pos=%s",
                    self.name, symbol, pos,
                )
                self.broker.place_order(
                    strategy_name=self.name,
                    tradingsymbol=pos["tradingsymbol"],
                    exchange=self.config.get("exchange", "NFO"),
                    transaction_type="SELL" if pos["direction"] == "LONG" else "BUY",
                    quantity=pos["quantity"],
                    order_type="MARKET",
                    product=self.config.get("order_type", "MIS"),
                    paper_trade=self.paper_trade,
                )
            self._open_positions = {}
            self.state.set_json("open_positions", {})
        except Exception as e:
            self.logger.error("%s: on_market_close error: %s", self.name, e)

    def on_candle(self, symbol: str, candle: dict) -> None:
        try:
            history = self.candles.history(symbol, self.get_timeframe(), n=self.get_lookback()) if self.candles else []

            max_trades = self.config.get("max_trades_per_day", 4)
            max_positions = self.config.get("max_open_positions", 2)

            if self._trades_today >= max_trades:
                return
            if len(self._open_positions) >= max_positions:
                return
            if symbol in self._open_positions:
                return

            signal = self._compute_signal(symbol, history)
            if signal:
                self._enter_trade(symbol, signal, candle["close"])
        except Exception as e:
            self.logger.error("%s: on_candle error: %s", self.name, e)

    def on_tick(self, tick: dict) -> None:
        try:
            symbol = tick.get("symbol")
            price = tick.get("last_price", 0)
            pos = self._open_positions.get(symbol)
            if not pos:
                return

            sl = pos["stop_loss"]
            target = pos["target1"]

            if pos["direction"] == "LONG":
                if price <= sl or price >= target:
                    self._exit_trade(symbol, pos, price)
            else:
                if price >= sl or price <= target:
                    self._exit_trade(symbol, pos, price)
        except Exception as e:
            self.logger.error("%s: on_tick error: %s", self.name, e)

    def on_order_update(self, order: dict) -> None:
        try:
            status = order.get("status")
            order_id = order.get("order_id")
            self.logger.info("%s: order update order_id=%s status=%s", self.name, order_id, status)
        except Exception as e:
            self.logger.error("%s: on_order_update error: %s", self.name, e)

    def _compute_signal(self, symbol: str, history: list) -> str | None:
        if len(history) < self.get_param("ema_slow", 21) + 5:
            return None

        closes = [c["close"] for c in history]
        df = pd.DataFrame({"close": closes})

        ema_fast = self.get_param("ema_fast", 9)
        ema_slow = self.get_param("ema_slow", 21)
        rsi_period = self.get_param("rsi_period", 14)
        rsi_long = self.get_param("rsi_entry_long", 55)
        rsi_short = self.get_param("rsi_entry_short", 45)

        df[f"ema{ema_fast}"] = ta_lib.trend.ema_indicator(df["close"], window=ema_fast)
        df[f"ema{ema_slow}"] = ta_lib.trend.ema_indicator(df["close"], window=ema_slow)
        df["rsi"] = ta_lib.momentum.rsi(df["close"], window=rsi_period)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        bullish_cross = prev[f"ema{ema_fast}"] <= prev[f"ema{ema_slow}"] and last[f"ema{ema_fast}"] > last[f"ema{ema_slow}"]
        bearish_cross = prev[f"ema{ema_fast}"] >= prev[f"ema{ema_slow}"] and last[f"ema{ema_fast}"] < last[f"ema{ema_slow}"]

        if bullish_cross and last["rsi"] > rsi_long:
            return "LONG"
        if bearish_cross and last["rsi"] < rsi_short:
            return "SHORT"
        return None

    def _enter_trade(self, symbol: str, direction: str, price: float):
        sl_pct = self.get_param("sl_pct", 0.35) / 100
        target_pct = self.get_param("target1_pct", 0.50) / 100

        if direction == "LONG":
            sl = price * (1 - sl_pct)
            target = price * (1 + target_pct)
            tx_type = "BUY"
        else:
            sl = price * (1 + sl_pct)
            target = price * (1 - target_pct)
            tx_type = "SELL"

        quantity = 50  # placeholder — real impl resolves lot size from instruments CSV
        order_id = self.broker.place_order(
            strategy_name=self.name,
            tradingsymbol=symbol,
            exchange=self.config.get("exchange", "NFO"),
            transaction_type=tx_type,
            quantity=quantity,
            order_type="MARKET",
            product=self.config.get("order_type", "MIS"),
            paper_trade=self.paper_trade,
        )

        self._open_positions[symbol] = {
            "tradingsymbol": symbol,
            "direction": direction,
            "entry_price": price,
            "stop_loss": sl,
            "target1": target,
            "quantity": quantity,
            "order_id": order_id,
        }
        self._trades_today += 1
        self.state.set("trades_today", self._trades_today)
        self.state.set_json("open_positions", self._open_positions)

        self.logger.info(
            "%s: ENTRY | symbol=%s dir=%s price=%.2f sl=%.2f target=%.2f order_id=%s",
            self.name, symbol, direction, price, sl, target, order_id,
        )

    def _exit_trade(self, symbol: str, pos: dict, price: float):
        tx_type = "SELL" if pos["direction"] == "LONG" else "BUY"
        order_id = self.broker.place_order(
            strategy_name=self.name,
            tradingsymbol=pos["tradingsymbol"],
            exchange=self.config.get("exchange", "NFO"),
            transaction_type=tx_type,
            quantity=pos["quantity"],
            order_type="MARKET",
            product=self.config.get("order_type", "MIS"),
            paper_trade=self.paper_trade,
        )

        pnl = (price - pos["entry_price"]) * pos["quantity"]
        if pos["direction"] == "SHORT":
            pnl = -pnl

        self.logger.info(
            "%s: EXIT | symbol=%s price=%.2f pnl=%.2f order_id=%s",
            self.name, symbol, price, pnl, order_id,
        )
        del self._open_positions[symbol]
        self.state.set_json("open_positions", self._open_positions)
