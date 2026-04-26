import logging
from datetime import datetime, date
from zoneinfo import ZoneInfo

from core.base_strategy import BaseStrategy

IST = ZoneInfo("Asia/Kolkata")

ENTRY_SLOTS = [
    (9,  30, 0.40),
    (10, 30, 0.50),
    (11, 30, 0.60),
    (12, 30, 0.70),
]
EXIT_HOUR, EXIT_MINUTE = 15, 0


class NiftyExpiryStraddle(BaseStrategy):
    def __init__(self, config, broker, state, logger):
        super().__init__(config, broker, state, logger)
        self._slots_entered: list[bool] = [False] * len(ENTRY_SLOTS)
        self._straddles: list[dict] = []
        self._today_instruments: list[dict] = []
        self._exit_triggered: bool = False

    # -------------------------------------------------------------------------
    # Lifecycle hooks
    # -------------------------------------------------------------------------

    def on_start(self) -> None:
        self._slots_entered = self.state.get_json("slots_entered", [False] * len(ENTRY_SLOTS))
        self._straddles = self.state.get_json("straddles", [])
        self._exit_triggered = bool(self.state.get_int("exit_triggered", 0))
        self._load_today_instruments()
        self.logger.info("%s started | paper_trade=%s | expiry_day=%s", self.name, self.paper_trade, self._is_expiry_day())

    def on_stop(self) -> None:
        self._persist_state()
        self.logger.info("%s stopped", self.name)

    def on_market_open(self) -> None:
        self._slots_entered = [False] * len(ENTRY_SLOTS)
        self._straddles = []
        self._exit_triggered = False
        self._persist_state()
        self._load_today_instruments()
        self.logger.info("%s: market open reset | expiry_day=%s", self.name, self._is_expiry_day())

    def on_market_close(self) -> None:
        # Safety net — 3 PM handler in on_candle should have already run
        try:
            self._close_all_positions(reason="market_close_safety_net")
        except Exception as e:
            self.logger.error("%s: on_market_close error: %s", self.name, e)

    # -------------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------------

    def on_candle(self, symbol: str, candle: dict) -> None:
        try:
            if not self._is_expiry_day():
                return

            now = datetime.now(IST)
            spot = candle["close"]

            # 3 PM force-exit
            if not self._exit_triggered and (now.hour, now.minute) >= (EXIT_HOUR, EXIT_MINUTE):
                self._close_all_positions(reason="3pm_scheduled_exit")
                return

            if self._exit_triggered:
                return

            # Check entry slots — only fire when the candle time matches the slot
            for slot_idx, (h, m, sl_pct) in enumerate(ENTRY_SLOTS):
                if self._slots_entered[slot_idx]:
                    continue
                if now.hour == h and now.minute == m:
                    self._enter_straddle(slot_idx, sl_pct, spot)

            # SL monitoring for open legs
            self._check_sl()

        except Exception as e:
            self.logger.error("%s: on_candle error: %s", self.name, e)

    def on_tick(self, tick: dict) -> None:
        # SL monitoring is done via LTP poll in on_candle; nothing to do here
        pass

    def on_order_update(self, order: dict) -> None:
        try:
            self.logger.info(
                "%s: order update | order_id=%s status=%s",
                self.name, order.get("order_id"), order.get("status"),
            )
        except Exception as e:
            self.logger.error("%s: on_order_update error: %s", self.name, e)

    # -------------------------------------------------------------------------
    # Core logic
    # -------------------------------------------------------------------------

    def _load_today_instruments(self) -> None:
        today = datetime.now(IST).date()
        instruments = self.broker.get_instruments("NFO")
        self._today_instruments = [
            inst for inst in instruments
            if inst.get("name") == "NIFTY" and inst.get("expiry") == today
        ]
        count = len(self._today_instruments)
        if count == 0:
            self.logger.info("%s: no Nifty expiry today (%s), strategy will idle", self.name, today)
        else:
            self.logger.info("%s: found %d Nifty option contracts expiring today (%s)", self.name, count, today)

    def _is_expiry_day(self) -> bool:
        return len(self._today_instruments) > 0

    def _get_atm_strike(self, spot: float) -> int:
        gap = self.get_param("strike_gap", 50)
        return round(spot / gap) * gap

    def _find_option_symbol(self, strike: int, option_type: str) -> str | None:
        for inst in self._today_instruments:
            if inst.get("strike") == strike and inst.get("instrument_type") == option_type:
                return inst["tradingsymbol"]
        return None

    def _enter_straddle(self, slot_idx: int, sl_pct: float, spot: float) -> None:
        strike = self._get_atm_strike(spot)
        ce_sym = self._find_option_symbol(strike, "CE")
        pe_sym = self._find_option_symbol(strike, "PE")

        if not ce_sym or not pe_sym:
            self.logger.warning(
                "%s: could not find ATM options | strike=%s ce=%s pe=%s",
                self.name, strike, ce_sym, pe_sym,
            )
            return

        ltp = self.broker.get_ltp([ce_sym, pe_sym])
        ce_ltp = ltp.get(ce_sym, 0.0)
        pe_ltp = ltp.get(pe_sym, 0.0)

        quantity = self.get_param("lot_size", 75)
        exchange = self.config.get("exchange", "NFO")
        product = self.config.get("order_type", "MIS")

        ce_order_id = self.broker.place_order(
            strategy_name=self.name,
            tradingsymbol=ce_sym,
            exchange=exchange,
            transaction_type="SELL",
            quantity=quantity,
            order_type="MARKET",
            product=product,
            paper_trade=self.paper_trade,
        )
        pe_order_id = self.broker.place_order(
            strategy_name=self.name,
            tradingsymbol=pe_sym,
            exchange=exchange,
            transaction_type="SELL",
            quantity=quantity,
            order_type="MARKET",
            product=product,
            paper_trade=self.paper_trade,
        )

        straddle = {
            "slot": slot_idx,
            "sl_pct": sl_pct,
            "ce": {
                "tradingsymbol": ce_sym,
                "entry_price": ce_ltp,
                "sl_price": round(ce_ltp * (1 + sl_pct), 2),
                "quantity": quantity,
                "order_id": ce_order_id,
                "open": True,
            },
            "pe": {
                "tradingsymbol": pe_sym,
                "entry_price": pe_ltp,
                "sl_price": round(pe_ltp * (1 + sl_pct), 2),
                "quantity": quantity,
                "order_id": pe_order_id,
                "open": True,
            },
        }
        self._straddles.append(straddle)
        self._slots_entered[slot_idx] = True
        self._persist_state()

        self.logger.info(
            "%s: STRADDLE ENTRY | slot=%d sl_pct=%.0f%% strike=%d "
            "ce=%s entry=%.2f sl=%.2f | pe=%s entry=%.2f sl=%.2f",
            self.name, slot_idx, sl_pct * 100, strike,
            ce_sym, ce_ltp, straddle["ce"]["sl_price"],
            pe_sym, pe_ltp, straddle["pe"]["sl_price"],
        )

    def _check_sl(self) -> None:
        open_symbols = []
        for st in self._straddles:
            for leg_key in ("ce", "pe"):
                if st[leg_key]["open"]:
                    open_symbols.append(st[leg_key]["tradingsymbol"])

        if not open_symbols:
            return

        ltp = self.broker.get_ltp(open_symbols)

        for st in self._straddles:
            for leg_key in ("ce", "pe"):
                leg = st[leg_key]
                if not leg["open"]:
                    continue
                current_price = ltp.get(leg["tradingsymbol"])
                if current_price is None:
                    continue
                if current_price >= leg["sl_price"]:
                    self._close_leg(st, leg_key, current_price, reason="sl_hit")

    def _close_leg(self, straddle: dict, leg_key: str, current_price: float, reason: str) -> None:
        leg = straddle[leg_key]
        exchange = self.config.get("exchange", "NFO")
        product = self.config.get("order_type", "MIS")

        order_id = self.broker.place_order(
            strategy_name=self.name,
            tradingsymbol=leg["tradingsymbol"],
            exchange=exchange,
            transaction_type="BUY",
            quantity=leg["quantity"],
            order_type="MARKET",
            product=product,
            paper_trade=self.paper_trade,
        )
        leg["open"] = False
        self._persist_state()

        pnl = (leg["entry_price"] - current_price) * leg["quantity"]
        self.logger.info(
            "%s: LEG EXIT | reason=%s leg=%s symbol=%s entry=%.2f exit=%.2f pnl=%.2f order_id=%s",
            self.name, reason, leg_key.upper(), leg["tradingsymbol"],
            leg["entry_price"], current_price, pnl, order_id,
        )

    def _close_all_positions(self, reason: str = "force_close") -> None:
        closed = 0
        for st in self._straddles:
            for leg_key in ("ce", "pe"):
                if st[leg_key]["open"]:
                    self._close_leg(st, leg_key, 0.0, reason=reason)
                    closed += 1
        self._exit_triggered = True
        self._persist_state()
        self.logger.info("%s: %s complete | legs_closed=%d", self.name, reason, closed)

    def _persist_state(self) -> None:
        self.state.set_json("straddles", self._straddles)
        self.state.set_json("slots_entered", self._slots_entered)
        self.state.set("exit_triggered", int(self._exit_triggered))
