import asyncio
import logging
import time
import uuid
from typing import Optional

logger = logging.getLogger("order_router")


class OrderRouter:
    def __init__(self, kite, paper_trade: bool = True):
        self._kite = kite
        self._paper_trade = paper_trade
        self._last_order_times: list[float] = []
        self._rate_limit = 10  # orders per second
        self._instrument_cache: dict[str, list] = {}

    def _throttle(self):
        now = time.monotonic()
        self._last_order_times = [t for t in self._last_order_times if now - t < 1.0]
        if len(self._last_order_times) >= self._rate_limit:
            sleep_for = 1.0 - (now - self._last_order_times[0])
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._last_order_times.append(time.monotonic())

    def place_order(
        self,
        strategy_name: str,
        tradingsymbol: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        product: str,
        price: float = 0,
        trigger_price: float = 0,
        paper_trade: Optional[bool] = None,
    ) -> str:
        use_paper = paper_trade if paper_trade is not None else self._paper_trade
        params = {
            "strategy": strategy_name,
            "tradingsymbol": tradingsymbol,
            "exchange": exchange,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "order_type": order_type,
            "product": product,
            "price": price,
            "trigger_price": trigger_price,
        }
        if use_paper:
            fake_id = f"PAPER-{uuid.uuid4().hex[:8].upper()}"
            logger.info("[PAPER] order intent | %s | order_id=%s", params, fake_id)
            return fake_id

        self._throttle()
        try:
            order_id = self._kite.place_order(
                tradingsymbol=tradingsymbol,
                exchange=exchange,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=order_type,
                product=product,
                price=price or None,
                trigger_price=trigger_price or None,
                variety=self._kite.VARIETY_REGULAR,
            )
            logger.info("[ORDER PLACED] strategy=%s order_id=%s params=%s", strategy_name, order_id, params)
            return order_id
        except Exception as e:
            logger.error("[ORDER ERROR] strategy=%s error=%s params=%s", strategy_name, e, params)
            asyncio.create_task(self._alert_and_retry(strategy_name, params, e))
            return ""

    async def _alert_and_retry(self, strategy_name: str, params: dict, original_error: Exception):
        from alerts.telegram import send_alert
        await send_alert(f"Order failed for {strategy_name}: {original_error}\nParams: {params}")

    def modify_order(self, order_id: str, quantity: int = None, price: float = None, order_type: str = None):
        if self._paper_trade:
            logger.info("[PAPER] modify_order order_id=%s quantity=%s price=%s", order_id, quantity, price)
            return order_id
        try:
            self._kite.modify_order(
                variety=self._kite.VARIETY_REGULAR,
                order_id=order_id,
                quantity=quantity,
                price=price,
                order_type=order_type,
            )
            return order_id
        except Exception as e:
            logger.error("[MODIFY ERROR] order_id=%s error=%s", order_id, e)
            return ""

    def cancel_order(self, order_id: str):
        if self._paper_trade:
            logger.info("[PAPER] cancel_order order_id=%s", order_id)
            return
        try:
            self._kite.cancel_order(variety=self._kite.VARIETY_REGULAR, order_id=order_id)
        except Exception as e:
            logger.error("[CANCEL ERROR] order_id=%s error=%s", order_id, e)

    def get_positions(self) -> dict:
        if self._paper_trade:
            return {"net": [], "day": []}
        return self._kite.positions()

    def get_margins(self) -> dict:
        return self._kite.margins()

    def get_instruments(self, exchange: str) -> list:
        if self._paper_trade:
            return []
        if exchange in self._instrument_cache:
            return self._instrument_cache[exchange]
        try:
            instruments = self._kite.instruments(exchange)
            self._instrument_cache[exchange] = instruments
            return instruments
        except Exception as e:
            logger.error("[INSTRUMENTS ERROR] exchange=%s error=%s", exchange, e)
            return []

    def get_ltp(self, symbols: list, exchange: str = "NFO") -> dict:
        if self._paper_trade:
            return {sym: 0.0 for sym in symbols}
        if not symbols:
            return {}
        try:
            keys = [f"{exchange}:{sym}" for sym in symbols]
            result = self._kite.ltp(keys)
            return {k.split(":", 1)[1]: v["last_price"] for k, v in result.items()}
        except Exception as e:
            logger.error("[LTP ERROR] symbols=%s error=%s", symbols, e)
            return {}
