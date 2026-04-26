import asyncio
import logging
from typing import Dict, List
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

logger = logging.getLogger("event_bus")
IST = ZoneInfo("Asia/Kolkata")


class EventBus:
    def __init__(self):
        self._strategies: Dict[str, object] = {}
        self._scheduler = AsyncIOScheduler(timezone=IST)

    def register(self, strategy):
        self._strategies[strategy.name] = strategy
        logger.info("EventBus: registered strategy %s", strategy.name)

    def unregister(self, name: str):
        self._strategies.pop(name, None)
        logger.info("EventBus: unregistered strategy %s", name)

    def start_scheduler(self):
        self._scheduler.add_job(self._emit_market_open, "cron", hour=9, minute=15, timezone=IST)
        self._scheduler.add_job(self._emit_market_close, "cron", hour=15, minute=30, timezone=IST)
        self._scheduler.start()

    def stop_scheduler(self):
        self._scheduler.shutdown(wait=False)

    async def emit_candle(self, symbol: str, timeframe: str, candle: dict):
        tasks = []
        for name, strategy in list(self._strategies.items()):
            if symbol in strategy.get_instruments() and strategy.get_timeframe() == timeframe:
                tasks.append(self._safe_on_candle(strategy, symbol, candle))
        if tasks:
            await asyncio.gather(*tasks)

    async def emit_tick(self, tick: dict):
        tasks = [self._safe_on_tick(s, tick) for s in self._strategies.values()]
        if tasks:
            await asyncio.gather(*tasks)

    async def emit_order_update(self, order: dict):
        tasks = []
        for strategy in self._strategies.values():
            if strategy.name == order.get("tag"):
                tasks.append(self._safe_on_order_update(strategy, order))
        if tasks:
            await asyncio.gather(*tasks)

    async def _emit_market_open(self):
        logger.info("EventBus: market open")
        tasks = [self._safe_on_market_open(s) for s in self._strategies.values()]
        if tasks:
            await asyncio.gather(*tasks)

    async def _emit_market_close(self):
        logger.info("EventBus: market close")
        tasks = [self._safe_on_market_close(s) for s in self._strategies.values()]
        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_on_candle(self, strategy, symbol, candle):
        try:
            strategy.on_candle(symbol, candle)
        except Exception as e:
            logger.error("EventBus: on_candle error in %s: %s", strategy.name, e)

    async def _safe_on_tick(self, strategy, tick):
        try:
            strategy.on_tick(tick)
        except Exception as e:
            logger.error("EventBus: on_tick error in %s: %s", strategy.name, e)

    async def _safe_on_order_update(self, strategy, order):
        try:
            strategy.on_order_update(order)
        except Exception as e:
            logger.error("EventBus: on_order_update error in %s: %s", strategy.name, e)

    async def _safe_on_market_open(self, strategy):
        try:
            strategy.on_market_open()
        except Exception as e:
            logger.error("EventBus: on_market_open error in %s: %s", strategy.name, e)

    async def _safe_on_market_close(self, strategy):
        try:
            strategy.on_market_close()
        except Exception as e:
            logger.error("EventBus: on_market_close error in %s: %s", strategy.name, e)
