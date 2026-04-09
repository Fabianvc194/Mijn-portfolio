"""
trading.py – Asset-specifieke trading engine.

Verwerkt signalen van TradingView en vertaalt ze naar
exchange-orders, met inachtneming van:
  • limit orders met dynamische bid/ask pricing (BTC)
  • volatility spike filter (ETH)
  • position sizing via risicomanagement
  • trailing stop-loss activering bij buy-orders
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config import Config
from exchange import Exchange
from risk import (
    calculate_position_size,
    cancel_trailing_stop,
    register_trailing_stop,
)

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """Gestructureerd signaal vanuit de webhook payload."""
    market: str     # bijv. "BTC-EUR"
    action: str     # "buy" | "sell"
    risk_pct: float | None = None  # optioneel override


class TradingEngine:
    def __init__(self, exchange: Exchange) -> None:
        self.exchange = exchange

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def execute(self, signal: Signal) -> dict:
        """
        Hoofd-entrypoint: verwerk een trading-signaal.
        Retourneert een dict met het resultaat of de reden van blokkade.
        """
        market = signal.market.upper()
        action = signal.action.lower()

        # Valideer markt
        if market not in Config.MARKETS:
            msg = f"Markt {market} niet ondersteund"
            logger.warning(msg)
            return {"status": "rejected", "reason": msg}

        market_cfg = Config.MARKETS[market]

        # ----------------------------------------------------------
        # 1. Volatility Spike Filter (ETH)
        # ----------------------------------------------------------
        if market_cfg.get("volatility_filter"):
            ticker = self.exchange.get_ticker(market)
            spread = ticker["spread_pct"]
            max_spread = market_cfg["max_spread_pct"]
            if spread > max_spread:
                msg = (
                    f"Volatility filter: spread {spread:.4f}% "
                    f"> max {max_spread}% – trade geblokkeerd"
                )
                logger.warning(msg)
                return {"status": "blocked", "reason": msg, "spread_pct": spread}
            logger.info("[%s] Spread check OK: %.4f%% ≤ %.1f%%", market, spread, max_spread)

        # ----------------------------------------------------------
        # 2. Haal marktdata op
        # ----------------------------------------------------------
        ticker = self.exchange.get_ticker(market)
        bid, ask = ticker["bid"], ticker["ask"]

        # ----------------------------------------------------------
        # 3. Position sizing
        # ----------------------------------------------------------
        balance = self.exchange.get_balance("EUR")
        price = bid if action == "sell" else ask
        risk_pct = signal.risk_pct or Config.RISK_PCT
        amount = calculate_position_size(balance, price, risk_pct)

        if amount <= 0:
            msg = f"Onvoldoende saldo (EUR {balance:.2f}) voor trade op {market}"
            logger.warning(msg)
            return {"status": "rejected", "reason": msg}

        # ----------------------------------------------------------
        # 4. Dynamische bid/ask pricing (limit order)
        # ----------------------------------------------------------
        if action == "buy":
            # Bied iets boven de huidige bid voor prioriteit,
            # maar onder de ask om slippage te vermijden.
            order_price = round(bid + (ask - bid) * 0.25, 2)
        else:
            # Vraag iets onder de huidige ask
            order_price = round(ask - (ask - bid) * 0.25, 2)

        # ----------------------------------------------------------
        # 5. Plaats order
        # ----------------------------------------------------------
        logger.info(
            "Placing %s %s: %.8f @ %.2f EUR (risk=%.1f%%, balance=%.2f)",
            action, market, amount, order_price, risk_pct, balance,
        )
        result = self.exchange.place_limit_order(
            market=market,
            side=action,
            amount=round(amount, 8),
            price=order_price,
        )

        # ----------------------------------------------------------
        # 6. Trailing Stop-Loss (alleen na buy)
        # ----------------------------------------------------------
        if action == "buy":
            register_trailing_stop(
                market=market,
                entry_price=order_price,
                amount=round(amount, 8),
                exchange=self.exchange,
            )
            logger.info("Trailing stop geactiveerd voor %s", market)
        elif action == "sell":
            # Bij een expliciete sell: stop de trailing stop
            cancel_trailing_stop(market)

        return {
            "status": "executed",
            "market": market,
            "side": action,
            "amount": round(amount, 8),
            "price": order_price,
            "order": result,
        }
