"""
risk.py – Wiskundig risicomanagement.

Bevat:
  • Position sizing op basis van account-percentage
  • Trailing Stop-Loss monitoring (in-process)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

from config import Config
from exchange import Exchange

logger = logging.getLogger(__name__)


# ======================================================================
# Position Sizing
# ======================================================================

def calculate_position_size(
    balance_eur: float,
    price: float,
    risk_pct: float | None = None,
) -> float:
    """
    Bereken de positiegrootte in base-asset eenheden.

    Formule:
        allocation = balance × (risk_pct / 100)
        amount     = allocation / price

    Parameters
    ----------
    balance_eur : float
        Beschikbaar EUR saldo.
    price : float
        Huidige prijs van het asset in EUR.
    risk_pct : float, optional
        Percentage van de balance dat per trade wordt geriskeerd.
        Default: Config.RISK_PCT (standaard 2 %).

    Returns
    -------
    float  – hoeveelheid base-asset (bijv. BTC of ETH).
    """
    if risk_pct is None:
        risk_pct = Config.RISK_PCT

    allocation_eur = balance_eur * (risk_pct / 100.0)
    if price <= 0:
        return 0.0
    amount = allocation_eur / price
    return amount


# ======================================================================
# Trailing Stop-Loss Monitor
# ======================================================================

@dataclass
class TrailingStop:
    """
    Monitort de prijs en activeert een sell als de prijs daalt
    vanaf het hoogste punt met meer dan `trail_pct` procent.

    Werkt in een aparte daemon-thread zodat de Flask-server
    niet wordt geblokkeerd.
    """

    market: str
    entry_price: float
    amount: float
    trail_pct: float = field(default_factory=lambda: Config.TRAILING_STOP_PCT)
    poll_interval: float = 5.0  # seconden

    # intern
    _highest: float = field(init=False, repr=False, default=0.0)
    _active: bool = field(init=False, repr=False, default=False)
    _thread: threading.Thread | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        self._highest = self.entry_price

    # ------------------------------------------------------------------
    @property
    def stop_price(self) -> float:
        """Huidige stop-prijs: hoogste_punt × (1 – trail_pct/100)."""
        return self._highest * (1 - self.trail_pct / 100.0)

    # ------------------------------------------------------------------
    def start(self, exchange: Exchange) -> None:
        """Start de monitor-loop in een daemon thread."""
        if self._active:
            logger.warning("Trailing stop al actief voor %s", self.market)
            return

        self._active = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            args=(exchange,),
            daemon=True,
            name=f"trailing-stop-{self.market}",
        )
        self._thread.start()
        logger.info(
            "Trailing stop gestart: %s | entry=%.2f | trail=%.1f%%",
            self.market, self.entry_price, self.trail_pct,
        )

    def stop(self) -> None:
        """Deactiveer de monitor (thread stopt bij volgende poll)."""
        self._active = False
        logger.info("Trailing stop gestopt voor %s", self.market)

    # ------------------------------------------------------------------
    def _monitor_loop(self, exchange: Exchange) -> None:
        while self._active:
            try:
                current = exchange.get_price(self.market)

                # Werk high-water mark bij
                if current > self._highest:
                    self._highest = current
                    logger.debug(
                        "[%s] Nieuw hoogste punt: %.2f → stop @ %.2f",
                        self.market, self._highest, self.stop_price,
                    )

                # Trigger stop-loss
                if current <= self.stop_price:
                    logger.warning(
                        "[%s] TRAILING STOP TRIGGERED – prijs %.2f ≤ stop %.2f",
                        self.market, current, self.stop_price,
                    )
                    self._execute_stop(exchange, current)
                    self._active = False
                    return

            except Exception:
                logger.exception("[%s] Fout in trailing-stop loop", self.market)

            time.sleep(self.poll_interval)

    def _execute_stop(self, exchange: Exchange, price: float) -> None:
        """Plaats een limit sell iets onder de markt voor snelle fill."""
        sell_price = price * 0.999  # 0.1 % onder huidige prijs
        try:
            exchange.place_limit_order(
                market=self.market,
                side="sell",
                amount=self.amount,
                price=round(sell_price, 2),
            )
            logger.info(
                "[%s] Stop-loss sell geplaatst: %.8f @ %.2f",
                self.market, self.amount, sell_price,
            )
        except Exception:
            logger.exception("[%s] KRITIEK: Stop-loss order mislukt!", self.market)


# ======================================================================
# Registry – houdt actieve stops bij per market
# ======================================================================

_active_stops: dict[str, TrailingStop] = {}
_lock = threading.Lock()


def register_trailing_stop(
    market: str,
    entry_price: float,
    amount: float,
    exchange: Exchange,
    trail_pct: float | None = None,
) -> TrailingStop:
    """Maak en start een trailing stop; vervangt een eventuele bestaande."""
    with _lock:
        if market in _active_stops:
            _active_stops[market].stop()

        ts = TrailingStop(
            market=market,
            entry_price=entry_price,
            amount=amount,
            trail_pct=trail_pct if trail_pct is not None else Config.TRAILING_STOP_PCT,
        )
        ts.start(exchange)
        _active_stops[market] = ts
        return ts


def cancel_trailing_stop(market: str) -> None:
    """Stop een actieve trailing stop."""
    with _lock:
        if market in _active_stops:
            _active_stops.pop(market).stop()
