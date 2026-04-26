import logging
from zoneinfo import ZoneInfo

import pandas as pd
import ta as ta_lib

from core.base_strategy import BaseStrategy

IST = ZoneInfo("Asia/Kolkata")


class PositionalFutures(BaseStrategy):
    def __init__(self, config, broker, state, logger):
        super().__init__(config, broker, state, logger)
        self._candle_history: dict[str, list] = {}
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
        self.state.set("trades_today", 0)
        self.logger.info("%s: market open", self.name)

    def on_market_close(self) -> None:
        # Positional strategy holds overnight (NRML) — no forced close at 3:30 PM
        self.logger.info("%s: market close, holding overnight positions", self.name)

    def on_candle(self, symbol: str, candle: dict) -> None:
        try:
            history = self._candle_history.setdefault(symbol, [])
            history.append(candle)
            if len(history) > 300:
                history.pop(0)

            max_trades = self.config.get("max_trades_per_day", 2)
            max_positions = self.config.get("max_open_positions", 2)

            if self._trades_today >= max_trades:
                return
            if len(self._open_positions) >= max_positions:
                return

            signal = self._compute_signal(symbol, history)
            if signal and symbol not in self._open_positions:
                self._enter_trade(symbol, signal, candle["close"], history)
        except Exception as e:
            self.logger.error("%s: on_candle error: %s", self.name, e)

    def on_tick(self, tick: dict) -> None:
        try:
            symbol = tick.get("symbol")
            price = tick.get("last_price", 0)
            pos = self._open_positions.get(symbol)
            if not pos:
                return

            if pos["direction"] == "LONG" and price <= pos["stop_loss"]:
                self._exit_trade(symbol, pos, price, reason="SL")
            elif pos["direction"] == "SHORT" and price >= pos["stop_loss"]:
                self._exit_trade(symbol, pos, price, reason="SL")
        except Exception as e:
            self.logger.error("%s: on_tick error: %s", self.name, e)

    def on_order_update(self, order: dict) -> None:
        try:
            self.logger.info(
                "%s: order_update order_id=%s status=%s",
                self.name, order.get("order_id"), order.get("status"),
            )
        except Exception as e:
            self.logger.error("%s: on_order_update error: %s", self.name, e)

    def _compute_signal(self, symbol: str, history: list) -> str | None:
        ema_slow = self.get_param("ema_slow", 50)
        if len(history) < ema_slow + 5:
            return None

        closes = [c["close"] for c in history]
        df = pd.DataFrame({"close": closes})

        ema_fast = self.get_param("ema_fast", 20)
        rsi_period = self.get_param("rsi_period", 14)
        atr_period = self.get_param("atr_period", 14)

        highs = pd.Series([c["high"] for c in history])
        lows = pd.Series([c["low"] for c in history])

        df[f"ema{ema_fast}"] = ta_lib.trend.ema_indicator(df["close"], window=ema_fast)
        df[f"ema{ema_slow}"] = ta_lib.trend.ema_indicator(df["close"], window=ema_slow)
        df["rsi"] = ta_lib.momentum.rsi(df["close"], window=rsi_period)
        df["atr"] = ta_lib.volatility.average_true_range(highs, lows, df["close"], window=atr_period)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        rsi_ob = self.get_param("rsi_overbought", 70)
        rsi_os = self.get_param("rsi_oversold", 30)

        bullish = (
            prev[f"ema{ema_fast}"] <= prev[f"ema{ema_slow}"]
            and last[f"ema{ema_fast}"] > last[f"ema{ema_slow}"]
            and last["rsi"] < rsi_ob
        )
        bearish = (
            prev[f"ema{ema_fast}"] >= prev[f"ema{ema_slow}"]
            and last[f"ema{ema_fast}"] < last[f"ema{ema_slow}"]
            and last["rsi"] > rsi_os
        )

        if bullish:
            return "LONG"
        if bearish:
            return "SHORT"
        return None

    def _enter_trade(self, symbol: str, direction: str, price: float, history: list):
        atr_period = self.get_param("atr_period", 14)
        sl_mult = self.get_param("atr_sl_multiplier", 2.0)
        tgt_mult = self.get_param("atr_target_multiplier", 3.0)

        highs = pd.Series([c["high"] for c in history])
        lows = pd.Series([c["low"] for c in history])
        closes = pd.Series([c["close"] for c in history])
        atr_val = ta_lib.volatility.average_true_range(highs, lows, closes, window=atr_period).iloc[-1]

        if direction == "LONG":
            sl = price - sl_mult * atr_val
            target = price + tgt_mult * atr_val
            tx_type = "BUY"
        else:
            sl = price + sl_mult * atr_val
            target = price - tgt_mult * atr_val
            tx_type = "SELL"

        quantity = 50  # placeholder
        order_id = self.broker.place_order(
            strategy_name=self.name,
            tradingsymbol=symbol,
            exchange=self.config.get("exchange", "NFO"),
            transaction_type=tx_type,
            quantity=quantity,
            order_type="MARKET",
            product=self.config.get("order_type", "NRML"),
            paper_trade=self.paper_trade,
        )

        self._open_positions[symbol] = {
            "tradingsymbol": symbol,
            "direction": direction,
            "entry_price": price,
            "stop_loss": sl,
            "target": target,
            "quantity": quantity,
            "order_id": order_id,
        }
        self._trades_today += 1
        self.state.set("trades_today", self._trades_today)
        self.state.set_json("open_positions", self._open_positions)

        self.logger.info(
            "%s: ENTRY | symbol=%s dir=%s price=%.2f sl=%.2f target=%.2f atr=%.2f order_id=%s",
            self.name, symbol, direction, price, sl, target, atr_val, order_id,
        )

    def _exit_trade(self, symbol: str, pos: dict, price: float, reason: str = ""):
        tx_type = "SELL" if pos["direction"] == "LONG" else "BUY"
        order_id = self.broker.place_order(
            strategy_name=self.name,
            tradingsymbol=pos["tradingsymbol"],
            exchange=self.config.get("exchange", "NFO"),
            transaction_type=tx_type,
            quantity=pos["quantity"],
            order_type="MARKET",
            product=self.config.get("order_type", "NRML"),
            paper_trade=self.paper_trade,
        )

        pnl = (price - pos["entry_price"]) * pos["quantity"]
        if pos["direction"] == "SHORT":
            pnl = -pnl

        self.logger.info(
            "%s: EXIT | reason=%s symbol=%s price=%.2f pnl=%.2f order_id=%s",
            self.name, reason, symbol, price, pnl, order_id,
        )
        del self._open_positions[symbol]
        self.state.set_json("open_positions", self._open_positions)
