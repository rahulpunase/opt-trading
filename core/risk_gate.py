import os
import logging
from typing import Dict

logger = logging.getLogger("risk_gate")


class RiskGate:
    def __init__(self, redis_client):
        self._r = redis_client
        self._total_capital = float(os.getenv("TOTAL_CAPITAL", 500000))
        self._daily_loss_cap = float(os.getenv("GLOBAL_DAILY_LOSS_CAP_PCT", 0.03)) * self._total_capital
        self._max_margin_pct = float(os.getenv("MAX_MARGIN_UTILISATION_PCT", 0.70))
        self._strategies: Dict[str, object] = {}
        self._blocked = False

    def register_strategy(self, name: str, strategy_obj):
        self._strategies[name] = strategy_obj

    def can_trade(self, strategy_name: str) -> bool:
        if self._blocked:
            logger.warning("RiskGate: trading blocked globally (daily loss cap hit)")
            return False

        daily_pnl = self._get_daily_pnl()
        if daily_pnl <= -self._daily_loss_cap:
            logger.error(
                "RiskGate: daily loss cap breached (pnl=%.2f cap=%.2f) — blocking all strategies",
                daily_pnl, self._daily_loss_cap
            )
            self._trigger_emergency_stop()
            return False

        margin_used_pct = self._get_margin_used_pct()
        if margin_used_pct >= self._max_margin_pct:
            logger.warning(
                "RiskGate: margin utilisation %.1f%% >= limit %.1f%% — blocking new entries",
                margin_used_pct * 100, self._max_margin_pct * 100
            )
            return False

        return True

    def record_pnl(self, strategy_name: str, pnl_delta: float):
        key = "portfolio:daily_pnl"
        current = self._r.get(key)
        current_val = float(current) if current else 0.0
        self._r.set(key, current_val + pnl_delta)

    def reset_daily(self):
        self._r.set("portfolio:daily_pnl", 0)
        self._blocked = False
        logger.info("RiskGate: daily counters reset")

    def _get_daily_pnl(self) -> float:
        val = self._r.get("portfolio:daily_pnl")
        return float(val) if val else 0.0

    def _get_margin_used_pct(self) -> float:
        val = self._r.get("portfolio:margin_used_pct")
        return float(val) if val else 0.0

    def _trigger_emergency_stop(self):
        self._blocked = True
        for name, strategy in self._strategies.items():
            try:
                strategy.on_stop()
                logger.info("RiskGate: stopped strategy %s", name)
            except Exception as e:
                logger.error("RiskGate: error stopping %s: %s", name, e)
